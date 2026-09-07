"""Descubre WALK_OFF_HR desde MLB Schedule/Game Feed y crea MomentContext."""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models import CardEdition, CardEditionSourceType, CardEditionType, MomentContextSourceType, Player
from etl.loaders.core import upsert_player
from etl.services.moment_contexts import persist_moment_context
from etl.sources.mlb import MLBStatsApiClient

logger = logging.getLogger("etl.services.walk_off_hr_detector")
WALK_OFF_HR_DETECTOR_VERSION = "walk-off-hr-detector-1.1"
CARD_EDITION_VERSION = "edition-1.0"


@dataclass(frozen=True)
class ScheduledGame:
    game_pk: int
    game_date: date
    season: int


@dataclass(frozen=True)
class ConfirmedWalkOffHr:
    game: ScheduledGame
    at_bat_number: int
    batter_mlb_id: int
    facts: dict
    occurred_at: datetime


@dataclass(frozen=True)
class WalkOffHrDetectionFailure:
    game_pk: int
    at_bat_number: int
    batter_mlb_id: int
    reason: str
    kind: str = "FAILED"


@dataclass(frozen=True)
class WalkOffHrDetectionResult:
    selected: int
    confirmed: int
    created: int
    updated: int
    unchanged: int
    unconfirmed: int
    failed: int
    moment_context_ids: tuple[str, ...]
    failures: tuple[WalkOffHrDetectionFailure, ...]


def _integer(value):
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _integer_string(value):
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return _integer(value)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _score(result: dict, side: str) -> int | None:
    return _integer(result.get(f"{side}Score"))


def _final_games(schedule: dict) -> list[ScheduledGame]:
    games = []
    for day in schedule.get("dates", []):
        try:
            game_date = date.fromisoformat(day.get("date"))
        except (TypeError, ValueError):
            continue
        for item in day.get("games", []):
            game_pk = _integer(item.get("gamePk"))
            season = _integer_string(item.get("season"))
            if (
                item.get("status", {}).get("abstractGameState") == "Final"
                and game_pk is not None
                and season is not None
            ):
                games.append(ScheduledGame(game_pk, game_date, season))
    return sorted(games, key=lambda game: (game.game_date, game.game_pk))


def _batter_boxscore(feed: dict, batter_mlb_id: int) -> dict | None:
    players = feed.get("liveData", {}).get("boxscore", {}).get("teams", {}).get("home", {}).get("players", {})
    record = players.get(f"ID{batter_mlb_id}")
    batting = record.get("stats", {}).get("batting") if isinstance(record, dict) else None
    if not isinstance(batting, dict):
        return None
    required = ("plateAppearances", "atBats", "hits", "homeRuns", "rbi")
    normalized = {key: _integer(batting.get(key)) for key in required}
    if any(value is None or value < 0 for value in normalized.values()):
        return None
    return normalized


def _confirm_game(game: ScheduledGame, feed: dict) -> ConfirmedWalkOffHr | None:
    status = feed.get("gameData", {}).get("status", {})
    plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    if status.get("abstractGameState") != "Final" or not isinstance(plays, list) or not plays:
        return None
    play = plays[-1]
    about = play.get("about", {})
    result = play.get("result", {})
    batter_mlb_id = _integer(play.get("matchup", {}).get("batter", {}).get("id"))
    at_bat_number = _integer(about.get("atBatIndex"))
    inning = _integer(about.get("inning"))
    occurred_at = _parse_datetime(about.get("endTime"))
    if (
        batter_mlb_id is None or at_bat_number is None or inning is None or occurred_at is None
        or about.get("isComplete") is not True
        or str(about.get("halfInning", "")).lower() != "bottom"
        or result.get("eventType") != "home_run"
    ):
        return None
    post_home, post_away = _score(result, "home"), _score(result, "away")
    if post_home is None or post_away is None or post_home <= post_away:
        return None
    if len(plays) == 1:
        pre_home = pre_away = 0
    else:
        previous = plays[-2].get("result", {})
        pre_home, pre_away = _score(previous, "home"), _score(previous, "away")
    if pre_home is None or pre_away is None or pre_home > pre_away:
        return None
    linescore = feed.get("liveData", {}).get("linescore", {}).get("teams", {})
    final_home = _integer(linescore.get("home", {}).get("runs"))
    final_away = _integer(linescore.get("away", {}).get("runs"))
    if (final_home, final_away) != (post_home, post_away):
        return None
    batting = _batter_boxscore(feed, batter_mlb_id)
    if batting is None or batting["homeRuns"] < 1:
        return None
    facts = {
        "detector": {
            "version": WALK_OFF_HR_DETECTOR_VERSION,
            "discovery_source": "MLB_STATS_API_SCHEDULE",
            "confirmation_source": "MLB_STATS_API_GAME_FEED",
        },
        "schedule_candidate": {
            "game_pk": game.game_pk,
            "game_date": game.game_date.isoformat(),
            "season": game.season,
        },
        "game": {
            "game_pk": game.game_pk,
            "final_state": status.get("detailedState") or "Final",
            "inning": inning,
            "half_inning": "Bottom",
            "pre_home_score": pre_home,
            "pre_away_score": pre_away,
            "post_home_score": post_home,
            "post_away_score": post_away,
            "final_home_score": final_home,
            "final_away_score": final_away,
            "terminal_at_bat_index": at_bat_number,
            "batter_mlb_id": batter_mlb_id,
        },
        "batting": {
            "plate_appearances": batting["plateAppearances"],
            "at_bats": batting["atBats"],
            "hits": batting["hits"],
            "home_runs": batting["homeRuns"],
            "runs_batted_in": batting["rbi"],
            "walk_off": True,
        },
    }
    return ConfirmedWalkOffHr(game, at_bat_number, batter_mlb_id, facts, occurred_at)


def _ensure_player(db: Session, client: MLBStatsApiClient, mlb_id: int) -> Player:
    player = db.query(Player).filter_by(mlb_id=mlb_id).one_or_none()
    if player is not None:
        return player
    record = client.get_person(mlb_id)
    if record is None:
        raise ValueError(f"MLB no devolvió metadata para batter={mlb_id}")
    return upsert_player(db, record)


def _ensure_moment_edition(db: Session, confirmation: ConfirmedWalkOffHr) -> CardEdition:
    game = confirmation.game
    identity = {
        "season": game.season,
        "code": f"{game.season}_WALK_OFF_HR_{game.game_pk}_{confirmation.batter_mlb_id}_{confirmation.at_bat_number}",
        "version": CARD_EDITION_VERSION,
    }
    edition = db.query(CardEdition).filter_by(**identity).one_or_none()
    source_reference = f"mlb-game:{game.game_pk}:at-bat:{confirmation.at_bat_number}"
    if edition is None:
        edition = CardEdition(
            **identity,
            name="Walk-Off Home Run",
            edition_type=CardEditionType.MOMENT,
            is_active=False,
            source_type=CardEditionSourceType.GAME,
            source_reference=source_reference,
            starts_at=confirmation.occurred_at,
            ends_at=confirmation.occurred_at,
            metadata_payload={
                "detector_version": WALK_OFF_HR_DETECTOR_VERSION,
                "game_pk": game.game_pk,
                "at_bat_number": confirmation.at_bat_number,
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
        raise ValueError("la identidad de edición MOMENT tiene provenance incompatible")
    return edition


def detect_walk_off_home_runs(db: Session, client: MLBStatsApiClient, *, date_from: date, date_to: date) -> WalkOffHrDetectionResult:
    """Descubre juegos finalizados y persiste sus WALK_OFF_HR confirmados."""
    if date_to < date_from:
        raise ValueError("date_to debe ser mayor o igual a date_from")
    games = _final_games(client.get_schedule(date_from, date_to))
    counts = {key: 0 for key in ("confirmed", "created", "updated", "unchanged", "unconfirmed", "failed")}
    context_ids, failures = [], []
    for game in games:
        confirmation = None
        try:
            confirmation = _confirm_game(game, client.get_game_feed(game.game_pk))
            if confirmation is None:
                counts["unconfirmed"] += 1
                continue
            player = _ensure_player(db, client, confirmation.batter_mlb_id)
            edition = _ensure_moment_edition(db, confirmation)
            persisted = persist_moment_context(
                db,
                player_id=player.id,
                card_edition_id=edition.id,
                role="BATTER",
                occurred_at=confirmation.occurred_at,
                source_type=MomentContextSourceType.MLB_STATS_API,
                source_reference=f"mlb-stats-api:game/{game.game_pk}/feed/live",
                facts=confirmation.facts,
            )
            counts["confirmed"] += 1
            counts[persisted.status.lower()] += 1
            context_ids.append(persisted.moment_context_id)
        except Exception as exc:
            db.rollback()
            counts["failed"] += 1
            failures.append(
                WalkOffHrDetectionFailure(
                    game.game_pk,
                    confirmation.at_bat_number if confirmation else -1,
                    confirmation.batter_mlb_id if confirmation else -1,
                    str(exc),
                )
            )
            logger.exception("walk-off detector failed game_pk=%s", game.game_pk)
    return WalkOffHrDetectionResult(
        selected=len(games), confirmed=counts["confirmed"], created=counts["created"],
        updated=counts["updated"], unchanged=counts["unchanged"],
        unconfirmed=counts["unconfirmed"], failed=counts["failed"],
        moment_context_ids=tuple(context_ids), failures=tuple(failures),
    )
