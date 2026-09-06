"""Clutch neutral explícito para batter ratings-2.0."""

from dataclasses import dataclass

from etl.config.ratings_2 import (
    CLUTCH_NEUTRAL_RATING,
    CLUTCH_SOURCE,
    RATING_MODEL_VERSION,
)


@dataclass(frozen=True)
class BatterClutchRating:
    rating: int
    source: str
    sample_size: int
    model_version: str


def calculate_batter_clutch() -> BatterClutchRating:
    """Devuelve el baseline neutral; no consulta distribuciones ni aplica shrinkage."""
    return BatterClutchRating(
        rating=CLUTCH_NEUTRAL_RATING,
        source=CLUTCH_SOURCE,
        sample_size=0,
        model_version=RATING_MODEL_VERSION,
    )
