"""Genera CardRatingProfile para evaluaciones MULTI_HR_GAME existentes."""

from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models import MomentType
from etl.config.league_distributions import DISTRIBUTION_MODEL_VERSION
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.moment_profile_pipeline import (
    generate_moment_card_profiles,
)


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


def generate_multi_hr_moment_card_profiles(
    db: Session,
    *,
    rating_model_version: str = RATING_MODEL_VERSION,
    distribution_version: str = DISTRIBUTION_MODEL_VERSION,
) -> MultiHrMomentCardProfileBatchResult:
    """Resuelve PlayerRatings D-1 y genera perfiles para MULTI_HR_GAME."""
    result = generate_moment_card_profiles(
        db,
        moment_type=MomentType.MULTI_HR_GAME,
        rating_model_version=rating_model_version,
        distribution_version=distribution_version,
    )
    return MultiHrMomentCardProfileBatchResult(
        selected=result.selected,
        created=result.created,
        updated=result.updated,
        unchanged=result.unchanged,
        skipped_no_ratings=result.skipped_no_ratings,
        failed=result.failed,
        card_rating_profile_ids=result.card_rating_profile_ids,
        failures=tuple(
            MultiHrMomentCardProfileFailure(
                failure.moment_evaluation_id, failure.reason
            )
            for failure in result.failures
        ),
    )
