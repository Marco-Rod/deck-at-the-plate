"""Genera CardRatingProfile para evaluaciones MULTI_HR_GAME existentes."""

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import MomentEvaluation, MomentType
from etl.config.league_distributions import DISTRIBUTION_MODEL_VERSION
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.moment_card_profiles import generate_moment_card_rating_profile
from etl.services.player_ratings_resolver import resolve_player_ratings_as_of


logger = logging.getLogger("etl.services.multi_hr_moment_card_profiles")


@dataclass(frozen=True)
class MultiHrMomentCardProfileFailure:
    moment_evaluation_id: str
    reason: str


@dataclass(frozen=True)
class MultiHrMomentCardProfileBatchResult:
    selected: int
    created: int
    updated: int
    unchanged: int
    skipped_no_ratings: int
    failed: int
    card_rating_profile_ids: tuple[str, ...]
    failures: tuple[MultiHrMomentCardProfileFailure, ...]


def _game_date(evaluation: MomentEvaluation) -> date:
    raw_value = evaluation.moment_context.facts.get("game", {}).get("game_date")
    if not isinstance(raw_value, str):
        raise ValueError("MomentContext MULTI_HR_GAME no contiene game.game_date")
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise ValueError("MomentContext contiene game.game_date inválido") from exc


def generate_multi_hr_moment_card_profiles(
    db: Session,
    *,
    rating_model_version: str = RATING_MODEL_VERSION,
    distribution_version: str = DISTRIBUTION_MODEL_VERSION,
) -> MultiHrMomentCardProfileBatchResult:
    """Resuelve PlayerRatings D-1 y genera perfiles para MULTI_HR_GAME."""
    evaluations = (
        db.query(MomentEvaluation)
        .filter(MomentEvaluation.moment_type == MomentType.MULTI_HR_GAME)
        .order_by(MomentEvaluation.created_at.asc(), MomentEvaluation.id.asc())
        .all()
    )
    counts = {
        key: 0
        for key in ("created", "updated", "unchanged", "skipped_no_ratings", "failed")
    }
    profile_ids = []
    failures = []
    for evaluation in evaluations:
        try:
            with db.begin_nested():
                context = evaluation.moment_context
                if context is None:
                    raise ValueError("MomentEvaluation no tiene MomentContext")
                event_date = _game_date(evaluation)
                ratings = resolve_player_ratings_as_of(
                    db,
                    player_id=context.player_id,
                    role=context.role,
                    season=context.season,
                    as_of_date=event_date,
                    rating_model_version=rating_model_version,
                    distribution_version=distribution_version,
                )
                if ratings is None:
                    counts["skipped_no_ratings"] += 1
                    continue
                result = generate_moment_card_rating_profile(
                    db,
                    moment_evaluation_id=evaluation.id,
                    source_player_ratings_id=ratings.id,
                    commit=False,
                )
            counts[result.status.lower()] += 1
            profile_ids.append(result.card_rating_profile_id)
        except Exception as exc:
            counts["failed"] += 1
            failures.append(MultiHrMomentCardProfileFailure(evaluation.id, str(exc)))
            logger.exception(
                "multi-HR profile failed moment_evaluation_id=%s", evaluation.id
            )
    db.commit()
    return MultiHrMomentCardProfileBatchResult(
        selected=len(evaluations),
        created=counts["created"],
        updated=counts["updated"],
        unchanged=counts["unchanged"],
        skipped_no_ratings=counts["skipped_no_ratings"],
        failed=counts["failed"],
        card_rating_profile_ids=tuple(profile_ids),
        failures=tuple(failures),
    )
