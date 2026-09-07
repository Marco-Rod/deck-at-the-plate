"""Tier puro de performance; no representa rareza coleccionable de carta."""

from dataclasses import dataclass

from app.models.card import CardRarity
from etl.config.performance_tier_2 import (
    PERFORMANCE_TIER_MODEL_VERSION,
    PERFORMANCE_TIER_THRESHOLDS,
)


# Los nombres del enum se conservan temporalmente por compatibilidad. En este
# dominio representan bandas de performance, no escasez ni valor económico.
PerformanceTier = CardRarity


@dataclass(frozen=True)
class PerformanceTierResult:
    overall_rating: int
    performance_percentile: float
    performance_tier: PerformanceTier
    performance_tier_model_version: str = PERFORMANCE_TIER_MODEL_VERSION

    # Propiedades de transición para consumidores legacy de rarity2.py.
    @property
    def percentile(self) -> float:
        return self.performance_percentile

    @property
    def rarity(self) -> PerformanceTier:
        return self.performance_tier

    @property
    def rarity_model_version(self) -> str:
        return self.performance_tier_model_version


def performance_tier_from_percentile(percentile: float) -> PerformanceTier:
    """Aplica los boundaries inclusivos del modelo de performance tier."""
    if not 0 <= percentile <= 1:
        raise ValueError("percentile debe estar entre 0 y 1")
    if percentile >= PERFORMANCE_TIER_THRESHOLDS["DIAMOND"]:
        return PerformanceTier.DIAMOND
    if percentile >= PERFORMANCE_TIER_THRESHOLDS["GOLD"]:
        return PerformanceTier.GOLD
    if percentile >= PERFORMANCE_TIER_THRESHOLDS["SILVER"]:
        return PerformanceTier.SILVER
    if percentile >= PERFORMANCE_TIER_THRESHOLDS["BRONZE"]:
        return PerformanceTier.BRONZE
    return PerformanceTier.COMMON


def calculate_performance_tier(
    overall_rating: int, rating_distribution
) -> PerformanceTierResult:
    """Calcula mid-rank empírico conservando juntos los ratings empatados."""
    if isinstance(overall_rating, bool) or not isinstance(overall_rating, int):
        raise TypeError("overall_rating debe ser entero")
    if not 40 <= overall_rating <= 99:
        raise ValueError("overall_rating debe estar entre 40 y 99")

    histogram = {
        int(value): int(count)
        for value, count in (rating_distribution.population_histogram or {}).items()
    }
    if any(count <= 0 for count in histogram.values()):
        raise ValueError("population_histogram contiene conteos inválidos")
    population_size = int(rating_distribution.population_size)
    if not histogram or sum(histogram.values()) != population_size:
        raise ValueError("population_histogram no coincide con population_size")
    if overall_rating not in histogram:
        raise ValueError("overall_rating no pertenece a la distribución")

    below = sum(count for value, count in histogram.items() if value < overall_rating)
    tied = histogram[overall_rating]
    percentile = (below + 0.5 * tied) / population_size
    return PerformanceTierResult(
        overall_rating=overall_rating,
        performance_percentile=percentile,
        performance_tier=performance_tier_from_percentile(percentile),
    )
