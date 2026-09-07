"""Distribución idempotente de ratings para tiers relativos de performance."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from statistics import fmean
from collections import Counter

from sqlalchemy.orm import Session

from app.models import PlayerRatings, RatingDistribution
from etl.config.league_distributions import default_distribution_version
from etl.config.performance_tier_2 import (
    OVERALL_RATING_METRIC,
    PERFORMANCE_TIER_MODEL_VERSION,
)
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.percentiles import percentile


DECIMAL_STEP = Decimal("0.00000001")


@dataclass(frozen=True)
class RatingDistributionBuildResult:
    status: str
    rating_distribution_id: str | None
    population_size: int
    performance_tier_model_version: str

    @property
    def rarity_model_version(self) -> str:
        """Nombre legacy para consumidores que aún no migran al dominio tier."""
        return self.performance_tier_model_version


def _decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(DECIMAL_STEP, rounding=ROUND_HALF_UP)


def _summary(values: list[int]) -> dict:
    histogram = {
        str(value): count for value, count in sorted(Counter(values).items())
    }
    if sum(histogram.values()) != len(values):
        raise AssertionError("el histograma no representa la población completa")
    return {
        "population_size": len(values),
        "population_histogram": histogram,
        "minimum": _decimal(min(values)),
        "p05": _decimal(percentile(values, 0.05)),
        "p10": _decimal(percentile(values, 0.10)),
        "p25": _decimal(percentile(values, 0.25)),
        "p50": _decimal(percentile(values, 0.50)),
        "p75": _decimal(percentile(values, 0.75)),
        "p90": _decimal(percentile(values, 0.90)),
        "p95": _decimal(percentile(values, 0.95)),
        "maximum": _decimal(max(values)),
        "population_mean": _decimal(fmean(values)),
    }


def build_overall_rating_distribution(
    db: Session,
    *,
    season: int,
    role: str,
    data_start_date: date,
    data_end_date: date,
    rating_model_version: str = RATING_MODEL_VERSION,
    source_distribution_version: str | None = None,
    performance_tier_model_version: str = PERFORMANCE_TIER_MODEL_VERSION,
    rarity_model_version: str | None = None,
) -> RatingDistributionBuildResult:
    normalized_role = role.upper()
    if normalized_role not in {"BATTER", "PITCHER"}:
        raise ValueError("role debe ser batter o pitcher")
    if data_end_date < data_start_date:
        raise ValueError("data_end_date debe ser igual o posterior a data_start_date")
    source_version = source_distribution_version or default_distribution_version()
    tier_version = rarity_model_version or performance_tier_model_version
    identity = {
        "season": season,
        "role": normalized_role,
        "rating_model_version": rating_model_version,
        "source_distribution_version": source_version,
        # Nombre físico legacy; semánticamente versiona performance tier.
        "rarity_model_version": tier_version,
        "metric": OVERALL_RATING_METRIC,
        "data_start_date": data_start_date,
        "data_end_date": data_end_date,
    }
    values = [
        row.overall_rating
        for row in db.query(PlayerRatings).filter_by(
            season=season,
            role=normalized_role,
            rating_model_version=rating_model_version,
            distribution_version=source_version,
            data_start_date=data_start_date,
            data_end_date=data_end_date,
        ).all()
    ]
    if not values:
        return RatingDistributionBuildResult("SKIPPED_EMPTY", None, 0, tier_version)

    payload = _summary(values)
    existing = db.query(RatingDistribution).filter_by(**identity).one_or_none()
    if existing is None:
        existing = RatingDistribution(**identity, **payload)
        db.add(existing)
        db.commit()
        return RatingDistributionBuildResult("CREATED", existing.id, len(values), tier_version)
    if all(getattr(existing, field) == value for field, value in payload.items()):
        return RatingDistributionBuildResult("UNCHANGED", existing.id, len(values), tier_version)
    for field, value in payload.items():
        setattr(existing, field, value)
    db.commit()
    return RatingDistributionBuildResult("UPDATED", existing.id, len(values), tier_version)
