"""Genera CardRatingProfile para evaluaciones 10_STRIKEOUT_GAME existentes."""

from sqlalchemy.orm import Session

from app.models import MomentType
from etl.config.league_distributions import DISTRIBUTION_MODEL_VERSION
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.moment_profile_pipeline import (
    MomentProfileBatchResult,
    generate_moment_card_profiles,
)


def generate_ten_strikeout_moment_card_profiles(
    db: Session,
    *,
    rating_model_version: str = RATING_MODEL_VERSION,
    distribution_version: str = DISTRIBUTION_MODEL_VERSION,
) -> MomentProfileBatchResult:
    """Resuelve PlayerRatings D-1 y genera perfiles para juegos de 10+ K."""
    return generate_moment_card_profiles(
        db,
        moment_type=MomentType.TEN_STRIKEOUT_GAME,
        rating_model_version=rating_model_version,
        distribution_version=distribution_version,
    )
