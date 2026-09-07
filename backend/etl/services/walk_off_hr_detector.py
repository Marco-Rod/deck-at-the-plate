"""Detecta WALK_OFF_HR solo cuando Statcast y el feed MLB lo demuestran."""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models import (
    CardEdition,
    CardEditionSourceType,
    CardEditionType,
    MomentContextSourceType,
    Player,
    RawPitchEvent,
)
from etl.services.moment_contexts import persist_moment_context
from etl.sources.mlb import MLBStatsApiClient


logger = logging.getLogger("etl.services.walk_off_hr_detector")
WALK_OFF_HR_DETECTOR_VERSION = "walk-off-hr-detector-1.0"
CARD_EDITION_VERSION = "edition-1.0"


@dataclass(frozen=True)
class WalkOffHrCandidate:
    game_pk: int
    game_date: date
    season: int
    at_bat_number: int
    batter_mlb_id: int
    raw_pitch_event_id: str
    raw_payload_hash: str | None


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


def _batter_boxscore(feed: dict, batter_mlb_id: int) -> dict | None:
    players = (
        feed.get("liveData", {})
        .get("boxscore", {})
        .get("teams", {})
        .get("home", {})
        .get("players", {})
    )
    record = players.get(f"ID{batter_mlb_id}")
    if not isinstance(record, dict):
        return None
    batting = record.get("stats", {}).get("batting")
    if not isinstance(batting, dict):
        return None
    required = ("plateAppearances", "atBats", "hits", "homeRuns", "rbi")
    normalized = {key: _integer(batting.get(key)) for key in required}
    if any(value is None or value < 0 for value in normalized.values()):
        return None
    return normalized


def _confirm_candidate(
    candidate: WalkOffHrCandidate, feed: dict
) -> tuple[dict, datetime] | None:
    status = feed.get("gameData", {}).get("status", {})
    if status.get("abstractGameState") != "Final":
        return None
    plays = feed.get("liveData", {}).get("plays", {}).get("allPlays", [])
    if not isinstance(plays, list) or not plays:
        return None
    matching_index = len(plays) - 1
    play = plays[matching_index]
    feed_at_bat_index = _integer(play.get("about", {}).get("atBatIndex"))
    # Statcast usa `at_bat_number`; algunos feeds históricos exponen el índice
    # equivalente en base cero. Solo se toleran esas dos representaciones.
    if (
        feed_at_bat_index is None
        or candidate.at_bat_number not in {feed_at_bat_index, feed_at_bat_index + 1}
        or _integer(play.get("matchup", {}).get("batter", {}).get("id"))
        != candidate.batter_mlb_id
    ):
        return None
    about = play.get("about", {})
    result = play.get("result", {})
    if (
        about.get("isComplete") is not True
        or str(about.get("halfInning", "")).lower() != "bottom"
        or result.get("eventType") != "home_run"
    ):
        return None
    occurred_at = _parse_datetime(about.get("endTime"))
    inning = _integer(about.get("inning"))
    if occurred_at is None or inning is None:
        return None

    post_home = _score(result, "home")
    post_away = _score(result, "away")
    if post_home is None or post_away is None or post_home <= post_away:
        return None
    if matching_index == 0:
        pre_home = pre_away = 0
    else:
        previous_result = plays[matching_index - 1].get("result", {})
        pre_home = _score(previous_result, "home")
        pre_away = _score(previous_result, "away")
    if pre_home is None or pre_away is None or pre_home > pre_away:
        return None

    linescore = feed.get("liveData", {}).get("linescore", {}).get("teams", {})
    final_home = _integer(linescore.get("home", {}).get("runs"))
    final_away = _integer(linescore.get("away", {}).get("runs"))
    if (final_home, final_away) != (post_home, post_away):
        return None
    batting = _batter_boxscore(feed, candidate.batter_mlb_id)
    if batting is None or batting["homeRuns"] < 1:
        return None

    facts = {
        "detector": {
            "version": WALK_OFF_HR_DETECTOR_VERSION,
            "confirmation_source": "MLB_STATS_API_GAME_FEED",
        },
        "statcast_candidate": {
            "raw_pitch_event_id": candidate.raw_pitch_event_id,
            "game_pk": candidate.game_pk,
            "game_date": candidate.game_date.isoformat(),
            "at_bat_number": candidate.at_bat_number,
            "batter_mlb_id": candidate.batter_mlb_id,
            "event": "home_run",
            "raw_payload_hash": candidate.raw_payload_hash,
        },
        "game": {
            "game_pk": candidate.game_pk,
            "final_state": status.get("detailedState") or "Final",
            "inning": inning,
            "half_inning": "Bottom",
            "pre_home_score": pre_home,
            "pre_away_score": pre_away,
            "post_home_score": post_home,
            "post_away_score": post_away,
            "final_home_score": final_home,
            "final_away_score": final_away,
            "terminal_at_bat_index": candidate.at_bat_number,
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
    return facts, occurred_at


def _ensure_moment_edition(
    db: Session,
    *,
    season: int,
    candidate: WalkOffHrCandidate,
    occurred_at: datetime,
) -> CardEdition:
    identity = {
        "season": season,
        "code": (
            f"{season}_WALK_OFF_HR_{candidate.game_pk}_"
            f"{candidate.batter_mlb_id}_{candidate.at_bat_number}"
        ),
        "version": CARD_EDITION_VERSION,
    }
    edition = db.query(CardEdition).filter_by(**identity).one_or_none()
    source_reference = (
        f"mlb-game:{candidate.game_pk}:at-bat:{candidate.at_bat_number}"
    )
    if edition is None:
        edition = CardEdition(
            **identity,
            name="Walk-Off Home Run",
            edition_type=CardEditionType.MOMENT,
            is_active=False,
            source_type=CardEditionSourceType.GAME,
            source_reference=source_reference,
            starts_at=occurred_at,
            ends_at=occurred_at,
            metadata_payload={
                "detector_version": WALK_OFF_HR_DETECTOR_VERSION,
                "game_pk": candidate.game_pk,
                "at_bat_number": candidate.at_bat_number,
                "batter_mlb_id": candidate.batter_mlb_id,
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


def detect_walk_off_home_runs(
    db: Session,
    client: MLBStatsApiClient,
    *,
    date_from: date,
    date_to: date,
) -> WalkOffHrDetectionResult:
    """Confirma candidatos Statcast con MLB game feed y crea MomentContext."""
    if date_to < date_from:
        raise ValueError("date_to debe ser mayor o igual a date_from")
    rows = (
        db.query(RawPitchEvent)
        .filter(
            RawPitchEvent.game_date >= date_from,
            RawPitchEvent.game_date <= date_to,
            RawPitchEvent.event == "home_run",
        )
        .order_by(
            RawPitchEvent.game_pk,
            RawPitchEvent.at_bat_number,
            RawPitchEvent.pitch_number,
        )
        .all()
    )
    candidates_by_key = {}
    for row in rows:
        key = (int(row.game_pk), row.at_bat_number, row.batter_mlb_id)
        candidates_by_key[key] = WalkOffHrCandidate(
            game_pk=int(row.game_pk),
            game_date=row.game_date,
            season=row.season,
            at_bat_number=row.at_bat_number,
            batter_mlb_id=row.batter_mlb_id,
            raw_pitch_event_id=row.id,
            raw_payload_hash=row.raw_payload_hash,
        )
    candidates = list(candidates_by_key.values())
    feeds = {}
    counts = {
        "confirmed": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "unconfirmed": 0,
        "failed": 0,
    }
    context_ids = []
    failures = []
    for candidate in candidates:
        try:
            if candidate.game_pk not in feeds:
                feeds[candidate.game_pk] = client.get_game_feed(candidate.game_pk)
            confirmation = _confirm_candidate(candidate, feeds[candidate.game_pk])
            if confirmation is None:
                counts["unconfirmed"] += 1
                failures.append(
                    WalkOffHrDetectionFailure(
                        candidate.game_pk,
                        candidate.at_bat_number,
                        candidate.batter_mlb_id,
                        "MLB_GAME_FEED_NO_CONFIRMA_WALK_OFF_HR",
                        "UNCONFIRMED",
                    )
                )
                continue
            player = (
                db.query(Player)
                .filter_by(mlb_id=candidate.batter_mlb_id)
                .one_or_none()
            )
            if player is None:
                raise ValueError(
                    f"Player inexistente para mlb_id={candidate.batter_mlb_id}"
                )
            facts, occurred_at = confirmation
            edition = _ensure_moment_edition(
                db,
                season=candidate.season,
                candidate=candidate,
                occurred_at=occurred_at,
            )
            persisted = persist_moment_context(
                db,
                player_id=player.id,
                card_edition_id=edition.id,
                role="BATTER",
                occurred_at=occurred_at,
                source_type=MomentContextSourceType.MLB_STATS_API,
                source_reference=(
                    f"mlb-stats-api:game/{candidate.game_pk}/feed/live"
                ),
                facts=facts,
            )
            counts["confirmed"] += 1
            counts[persisted.status.lower()] += 1
            context_ids.append(persisted.moment_context_id)
        except Exception as exc:
            db.rollback()
            counts["failed"] += 1
            failures.append(
                WalkOffHrDetectionFailure(
                    candidate.game_pk,
                    candidate.at_bat_number,
                    candidate.batter_mlb_id,
                    str(exc),
                )
            )
            logger.exception(
                "walk-off detector failed game_pk=%s at_bat=%s batter=%s",
                candidate.game_pk,
                candidate.at_bat_number,
                candidate.batter_mlb_id,
            )
    return WalkOffHrDetectionResult(
        selected=len(candidates),
        confirmed=counts["confirmed"],
        created=counts["created"],
        updated=counts["updated"],
        unchanged=counts["unchanged"],
        unconfirmed=counts["unconfirmed"],
        failed=counts["failed"],
        moment_context_ids=tuple(context_ids),
        failures=tuple(failures),
    )
