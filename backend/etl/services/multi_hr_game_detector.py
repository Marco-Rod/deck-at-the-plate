"""Descubre juegos de 2+ HR desde MLB Schedule/Game Feed."""

import logging
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models import (
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
    MomentContextSourceType,
)
from etl.services.moment_contexts import persist_moment_context
from etl.services.walk_off_hr_detector import (
    CARD_EDITION_VERSION,
    ScheduledGame,
    _ensure_player,
    _final_games,
    _integer,
    _parse_datetime,
)
from etl.sources.mlb import MLBStatsApiClient


logger = logging.getLogger("etl.services.multi_hr_game_detector")
MULTI_HR_GAME_DETECTOR_VERSION = "multi-hr-game-detector-1.0"


@dataclass(frozen=True)
class ConfirmedMultiHrGame:
    game: ScheduledGame
    batter_mlb_id: int
    facts: dict
    occurred_at: datetime
    final_at_bat_number: int


@dataclass(frozen=True)
class MultiHrGameDetectionFailure:
    game_pk: int
    batter_mlb_id: int
    reason: str


@dataclass(frozen=True)
class MultiHrGameDetectionResult:
    selected: int
    confirmed: int
    created: int
    updated: int
    unchanged: int
    unconfirmed: int
    failed: int
    moment_context_ids: tuple[str, ...]
    failures: tuple[MultiHrGameDetectionFailure, ...]


def _boxscore_batters(feed: dict) -> dict[int, dict]:
    teams = feed.get("liveData", {}).get("boxscore", {}).get("teams", {})
    batters = {}
    for side in ("away", "home"):
        players = teams.get(side, {}).get("players", {})
        if not isinstance(players, dict):
            continue
        for record in players.values():
            if not isinstance(record, dict):
                continue
            batter_mlb_id = _integer(record.get("person", {}).get("id"))
            batting = record.get("stats", {}).get("batting")
            if batter_mlb_id is None or not isinstance(batting, dict):
                continue
            fields = {
                "plate_appearances": _integer(batting.get("plateAppearances")),
                "at_bats": _integer(batting.get("atBats")),
                "hits": _integer(batting.get("hits")),
                "home_runs": _integer(batting.get("homeRuns")),
                "runs_batted_in": _integer(batting.get("rbi")),
            }
            if all(value is not None and value >= 0 for value in fields.values()):
                batters[batter_mlb_id] = fields
    return batters


def _home_run_plays(feed: dict) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}
    plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    if not isinstance(plays, list):
        return grouped
    for play_index, play in enumerate(plays):
        about = play.get("about", {})
        if (
            about.get("isComplete") is not True
            or play.get("result", {}).get("eventType") != "home_run"
        ):
            continue
        batter_mlb_id = _integer(
            play.get("matchup", {}).get("batter", {}).get("id")
        )
        at_bat_index = _integer(about.get("atBatIndex"))
        inning = _integer(about.get("inning"))
        occurred_at = _parse_datetime(about.get("endTime"))
        half_inning = str(about.get("halfInning", "")).strip().lower()
        if (
            batter_mlb_id is None
            or at_bat_index is None
            or inning is None
            or occurred_at is None
            or half_inning not in {"top", "bottom"}
        ):
            continue
        result = play.get("result", {})
        previous_result = (
            plays[play_index - 1].get("result", {}) if play_index > 0 else {}
        )
        pre_home_score = (
            _integer(previous_result.get("homeScore")) if play_index > 0 else 0
        )
        pre_away_score = (
            _integer(previous_result.get("awayScore")) if play_index > 0 else 0
        )
        grouped.setdefault(batter_mlb_id, []).append(
            {
                "inning": inning,
                "half_inning": half_inning.title(),
                "at_bat_index": at_bat_index,
                "occurred_at": occurred_at,
                "runs_batted_in": _integer(result.get("rbi")),
                "pre_home_score": pre_home_score,
                "pre_away_score": pre_away_score,
                "post_home_score": _integer(result.get("homeScore")),
                "post_away_score": _integer(result.get("awayScore")),
            }
        )
    return grouped


def _confirm_game(
    game: ScheduledGame, feed: dict
) -> list[ConfirmedMultiHrGame]:
    status = feed.get("gameData", {}).get("status", {})
    if status.get("abstractGameState") != "Final":
        return []
    boxscore = _boxscore_batters(feed)
    home_runs_by_batter = _home_run_plays(feed)
    all_plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    if not isinstance(all_plays, list):
        return []
    innings = [
        inning
        for play in all_plays
        if (inning := _integer(play.get("about", {}).get("inning"))) is not None
    ]
    inning_count = _integer(
        feed.get("liveData", {}).get("linescore", {}).get("currentInning")
    ) or (max(innings) if innings else None)
    if inning_count is None:
        return []

    confirmations = []
    for batter_mlb_id, home_runs in sorted(home_runs_by_batter.items()):
        batting = boxscore.get(batter_mlb_id)
        if (
            batting is None
            or len(home_runs) < 2
            or batting["home_runs"] != len(home_runs)
        ):
            continue
        ordered_home_runs = sorted(home_runs, key=lambda item: item["at_bat_index"])
        occurred_at = ordered_home_runs[-1]["occurred_at"]
        facts = {
            "detector": {
                "version": MULTI_HR_GAME_DETECTOR_VERSION,
                "discovery_source": "MLB_STATS_API_SCHEDULE",
                "confirmation_source": "MLB_STATS_API_GAME_FEED",
            },
            "game": {
                "game_pk": game.game_pk,
                "game_date": game.game_date.isoformat(),
                "season": game.season,
                "final_state": status.get("detailedState") or "Final",
                "inning_count": inning_count,
            },
            "batting": batting,
            "home_runs": [
                {
                    "inning": item["inning"],
                    "half_inning": item["half_inning"],
                    "at_bat_index": item["at_bat_index"],
                    "occurred_at": item["occurred_at"].isoformat(),
                    "runs_batted_in": item["runs_batted_in"],
                    "pre_home_score": item["pre_home_score"],
                    "pre_away_score": item["pre_away_score"],
                    "post_home_score": item["post_home_score"],
                    "post_away_score": item["post_away_score"],
                }
                for item in ordered_home_runs
            ],
        }
        confirmations.append(
            ConfirmedMultiHrGame(
                game=game,
                batter_mlb_id=batter_mlb_id,
                facts=facts,
                occurred_at=occurred_at,
                final_at_bat_number=ordered_home_runs[-1]["at_bat_index"],
            )
        )
    return confirmations


def _ensure_moment_edition(
    db: Session, confirmation: ConfirmedMultiHrGame
) -> CardEdition:
    game = confirmation.game
    identity = {
        "season": game.season,
        "code": (
            f"{game.season}_MULTI_HR_GAME_{game.game_pk}_"
            f"{confirmation.batter_mlb_id}"
        ),
        "version": CARD_EDITION_VERSION,
    }
    edition = db.query(CardEdition).filter_by(**identity).one_or_none()
    source_reference = (
        f"mlb-game:{game.game_pk}:batter:{confirmation.batter_mlb_id}"
    )
    if edition is None:
        edition = CardEdition(
            **identity,
            name="Multi-Home Run Game",
            edition_type=CardEditionType.MOMENT,
            is_active=False,
            source_type=CardEditionSourceType.GAME,
            source_reference=source_reference,
            starts_at=confirmation.occurred_at,
            ends_at=confirmation.occurred_at,
            metadata_payload={
                "detector_version": MULTI_HR_GAME_DETECTOR_VERSION,
                "game_pk": game.game_pk,
                "batter_mlb_id": confirmation.batter_mlb_id,
            },
        )
        db.add(edition)
        db.flush()
    elif (
        edition.edition_type != CardEditionType.MOMENT
        or edition.source_type != CardEditionSourceType.GAME
        or edition.source_reference != source_reference
    ):
        raise ValueError("la identidad de edición MULTI_HR_GAME es incompatible")
    return edition


def detect_multi_hr_games(
    db: Session,
    client: MLBStatsApiClient,
    *,
    date_from: date,
    date_to: date,
) -> MultiHrGameDetectionResult:
    """Persiste un MomentContext por bateador con 2+ HR confirmados en un juego."""
    if date_to < date_from:
        raise ValueError("date_to debe ser mayor o igual a date_from")
    games = _final_games(client.get_schedule(date_from, date_to))
    counts = {
        key: 0
        for key in (
            "confirmed",
            "created",
            "updated",
            "unchanged",
            "unconfirmed",
            "failed",
        )
    }
    context_ids = []
    failures = []
    for game in games:
        try:
            confirmations = _confirm_game(game, client.get_game_feed(game.game_pk))
        except Exception as exc:
            counts["failed"] += 1
            failures.append(MultiHrGameDetectionFailure(game.game_pk, -1, str(exc)))
            logger.exception("multi-HR detector failed game_pk=%s", game.game_pk)
            continue
        if not confirmations:
            counts["unconfirmed"] += 1
            continue
        for confirmation in confirmations:
            try:
                with db.begin_nested():
                    player = _ensure_player(db, client, confirmation.batter_mlb_id)
                    edition = _ensure_moment_edition(db, confirmation)
                    persisted = persist_moment_context(
                        db,
                        player_id=player.id,
                        card_edition_id=edition.id,
                        role="BATTER",
                        occurred_at=confirmation.occurred_at,
                        source_type=MomentContextSourceType.MLB_STATS_API,
                        source_reference=(
                            f"mlb-stats-api:game/{game.game_pk}/feed/live:"
                            f"batter/{confirmation.batter_mlb_id}"
                        ),
                        facts=confirmation.facts,
                        commit=False,
                    )
                counts["confirmed"] += 1
                counts[persisted.status.lower()] += 1
                context_ids.append(persisted.moment_context_id)
            except Exception as exc:
                counts["failed"] += 1
                failures.append(
                    MultiHrGameDetectionFailure(
                        game.game_pk, confirmation.batter_mlb_id, str(exc)
                    )
                )
                logger.exception(
                    "multi-HR detector failed game_pk=%s batter=%s",
                    game.game_pk,
                    confirmation.batter_mlb_id,
                )
    db.commit()
    return MultiHrGameDetectionResult(
        selected=len(games),
        confirmed=counts["confirmed"],
        created=counts["created"],
        updated=counts["updated"],
        unchanged=counts["unchanged"],
        unconfirmed=counts["unconfirmed"],
        failed=counts["failed"],
        moment_context_ids=tuple(context_ids),
        failures=tuple(failures),
    )
