"""Descubre actuaciones de pitcher con 10+ strikeouts desde MLB Game Feed."""

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


logger = logging.getLogger("etl.services.ten_strikeout_game_detector")
TEN_STRIKEOUT_GAME_DETECTOR_VERSION = "ten-strikeout-game-detector-1.0"
STRIKEOUT_EVENT_TYPES = {"strikeout", "strikeout_double_play"}


@dataclass(frozen=True)
class ConfirmedTenStrikeoutGame:
    game: ScheduledGame
    pitcher_mlb_id: int
    facts: dict
    occurred_at: datetime


@dataclass(frozen=True)
class TenStrikeoutGameDetectionFailure:
    game_pk: int
    pitcher_mlb_id: int
    reason: str


@dataclass(frozen=True)
class TenStrikeoutGameDetectionResult:
    selected: int
    confirmed: int
    created: int
    updated: int
    unchanged: int
    unconfirmed: int
    failed: int
    moment_context_ids: tuple[str, ...]
    failures: tuple[TenStrikeoutGameDetectionFailure, ...]


def _innings_pitched(value) -> str | None:
    normalized = str(value).strip() if value is not None else ""
    parts = normalized.split(".")
    if (
        len(parts) != 2
        or not parts[0].isdigit()
        or parts[1] not in {"0", "1", "2"}
    ):
        return None
    return normalized


def _boxscore_pitchers(feed: dict) -> dict[int, dict]:
    teams = feed.get("liveData", {}).get("boxscore", {}).get("teams", {})
    pitchers = {}
    for side in ("away", "home"):
        players = teams.get(side, {}).get("players", {})
        if not isinstance(players, dict):
            continue
        for record in players.values():
            if not isinstance(record, dict):
                continue
            pitcher_mlb_id = _integer(record.get("person", {}).get("id"))
            pitching = record.get("stats", {}).get("pitching")
            if pitcher_mlb_id is None or not isinstance(pitching, dict):
                continue
            fields = {
                "innings_pitched": _innings_pitched(pitching.get("inningsPitched")),
                "strikeouts": _integer(pitching.get("strikeOuts")),
                "batters_faced": _integer(pitching.get("battersFaced")),
                "hits": _integer(pitching.get("hits")),
                "walks": _integer(pitching.get("baseOnBalls")),
                "earned_runs": _integer(pitching.get("earnedRuns")),
            }
            if fields["innings_pitched"] is None or any(
                fields[key] is None or fields[key] < 0
                for key in (
                    "strikeouts",
                    "batters_faced",
                    "hits",
                    "walks",
                    "earned_runs",
                )
            ):
                continue
            pitches = _integer(pitching.get("pitchesThrown"))
            strikes = _integer(pitching.get("strikes"))
            if (
                pitches is not None
                and strikes is not None
                and 0 <= strikes <= pitches
            ):
                fields["pitches"] = pitches
                fields["strikes"] = strikes
            else:
                fields["pitches"] = None
                fields["strikes"] = None
            fields["team_side"] = side.upper()
            pitchers[pitcher_mlb_id] = fields
    return pitchers


def _strikeout_plays(feed: dict) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}
    plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    if not isinstance(plays, list):
        return grouped
    for play in plays:
        about = play.get("about", {})
        event_type = play.get("result", {}).get("eventType")
        if about.get("isComplete") is not True or event_type not in STRIKEOUT_EVENT_TYPES:
            continue
        pitcher_mlb_id = _integer(
            play.get("matchup", {}).get("pitcher", {}).get("id")
        )
        at_bat_index = _integer(about.get("atBatIndex"))
        inning = _integer(about.get("inning"))
        occurred_at = _parse_datetime(about.get("endTime"))
        half_inning = str(about.get("halfInning", "")).strip().lower()
        batter_mlb_id = _integer(
            play.get("matchup", {}).get("batter", {}).get("id")
        )
        if (
            pitcher_mlb_id is None
            or batter_mlb_id is None
            or at_bat_index is None
            or inning is None
            or occurred_at is None
            or half_inning not in {"top", "bottom"}
        ):
            continue
        grouped.setdefault(pitcher_mlb_id, []).append(
            {
                "inning": inning,
                "half_inning": half_inning.title(),
                "at_bat_index": at_bat_index,
                "batter_mlb_id": batter_mlb_id,
                "occurred_at": occurred_at,
            }
        )
    return grouped


def _confirm_game(
    game: ScheduledGame, feed: dict
) -> list[ConfirmedTenStrikeoutGame]:
    status = feed.get("gameData", {}).get("status", {})
    if status.get("abstractGameState") != "Final":
        return []
    linescore = feed.get("liveData", {}).get("linescore", {})
    teams = linescore.get("teams", {})
    home_score = _integer(teams.get("home", {}).get("runs"))
    away_score = _integer(teams.get("away", {}).get("runs"))
    inning_count = _integer(linescore.get("currentInning"))
    if home_score is None or away_score is None or inning_count is None:
        return []

    strikeouts_by_pitcher = _strikeout_plays(feed)
    confirmations = []
    for pitcher_mlb_id, pitching in sorted(_boxscore_pitchers(feed).items()):
        strikeouts = strikeouts_by_pitcher.get(pitcher_mlb_id, [])
        if pitching["strikeouts"] < 10 or len(strikeouts) != pitching["strikeouts"]:
            continue
        ordered = sorted(strikeouts, key=lambda item: item["at_bat_index"])
        team_score = home_score if pitching["team_side"] == "HOME" else away_score
        opponent_score = away_score if pitching["team_side"] == "HOME" else home_score
        pitching = {
            **pitching,
            "game_result": "WON" if team_score > opponent_score else "LOST",
        }
        facts = {
            "detector": {
                "version": TEN_STRIKEOUT_GAME_DETECTOR_VERSION,
                "discovery_source": "MLB_STATS_API_SCHEDULE",
                "confirmation_source": "MLB_STATS_API_GAME_FEED",
            },
            "game": {
                "game_pk": game.game_pk,
                "game_date": game.game_date.isoformat(),
                "season": game.season,
                "final_state": status.get("detailedState") or "Final",
                "inning_count": inning_count,
                "final_home_score": home_score,
                "final_away_score": away_score,
            },
            "pitching": pitching,
            "strikeouts": [
                {
                    "inning": item["inning"],
                    "half_inning": item["half_inning"],
                    "at_bat_index": item["at_bat_index"],
                    "batter_mlb_id": item["batter_mlb_id"],
                    "occurred_at": item["occurred_at"].isoformat(),
                }
                for item in ordered
            ],
        }
        confirmations.append(
            ConfirmedTenStrikeoutGame(
                game=game,
                pitcher_mlb_id=pitcher_mlb_id,
                facts=facts,
                occurred_at=ordered[-1]["occurred_at"],
            )
        )
    return confirmations


def _ensure_moment_edition(
    db: Session, confirmation: ConfirmedTenStrikeoutGame
) -> CardEdition:
    game = confirmation.game
    identity = {
        "season": game.season,
        "code": (
            f"{game.season}_10_STRIKEOUT_GAME_{game.game_pk}_"
            f"{confirmation.pitcher_mlb_id}"
        ),
        "version": CARD_EDITION_VERSION,
    }
    edition = db.query(CardEdition).filter_by(**identity).one_or_none()
    source_reference = (
        f"mlb-game:{game.game_pk}:pitcher:{confirmation.pitcher_mlb_id}"
    )
    if edition is None:
        edition = CardEdition(
            **identity,
            name="10-Strikeout Game",
            edition_type=CardEditionType.MOMENT,
            is_active=False,
            source_type=CardEditionSourceType.GAME,
            source_reference=source_reference,
            starts_at=confirmation.occurred_at,
            ends_at=confirmation.occurred_at,
            metadata_payload={
                "detector_version": TEN_STRIKEOUT_GAME_DETECTOR_VERSION,
                "game_pk": game.game_pk,
                "pitcher_mlb_id": confirmation.pitcher_mlb_id,
            },
        )
        db.add(edition)
        db.flush()
    elif (
        edition.edition_type != CardEditionType.MOMENT
        or edition.source_type != CardEditionSourceType.GAME
        or edition.source_reference != source_reference
    ):
        raise ValueError("la identidad de edición 10_STRIKEOUT_GAME es incompatible")
    return edition


def detect_ten_strikeout_games(
    db: Session,
    client: MLBStatsApiClient,
    *,
    date_from: date,
    date_to: date,
) -> TenStrikeoutGameDetectionResult:
    """Persiste un MomentContext por pitcher con 10+ K confirmados en un juego."""
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
            failures.append(
                TenStrikeoutGameDetectionFailure(game.game_pk, -1, str(exc))
            )
            logger.exception("10-K detector failed game_pk=%s", game.game_pk)
            continue
        if not confirmations:
            counts["unconfirmed"] += 1
            continue
        for confirmation in confirmations:
            try:
                with db.begin_nested():
                    player = _ensure_player(db, client, confirmation.pitcher_mlb_id)
                    edition = _ensure_moment_edition(db, confirmation)
                    persisted = persist_moment_context(
                        db,
                        player_id=player.id,
                        card_edition_id=edition.id,
                        role="PITCHER",
                        occurred_at=confirmation.occurred_at,
                        source_type=MomentContextSourceType.MLB_STATS_API,
                        source_reference=(
                            f"mlb-stats-api:game/{game.game_pk}/feed/live:"
                            f"pitcher/{confirmation.pitcher_mlb_id}"
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
                    TenStrikeoutGameDetectionFailure(
                        game.game_pk, confirmation.pitcher_mlb_id, str(exc)
                    )
                )
                logger.exception(
                    "10-K detector failed game_pk=%s pitcher=%s",
                    game.game_pk,
                    confirmation.pitcher_mlb_id,
                )
    db.commit()
    return TenStrikeoutGameDetectionResult(
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
