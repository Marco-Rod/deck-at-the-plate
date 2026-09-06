"""Política pura de rarity-2.0 basada en posición poblacional."""

from dataclasses import dataclass

from app.models.card import CardRarity
from etl.config.rarity_2 import RARITY_MODEL_VERSION, RARITY_THRESHOLDS


@dataclass(frozen=True)
class RarityResult:
    overall_rating: int
    percentile: float
    rarity: CardRarity
    rarity_model_version: str = RARITY_MODEL_VERSION


def rarity_from_percentile(percentile: float) -> CardRarity:
    """Aplica los boundaries inclusivos de rarity-2.0."""
    if not 0 <= percentile <= 1:
        raise ValueError("percentile debe estar entre 0 y 1")
    if percentile >= RARITY_THRESHOLDS["DIAMOND"]:
        return CardRarity.DIAMOND
    if percentile >= RARITY_THRESHOLDS["GOLD"]:
        return CardRarity.GOLD
    if percentile >= RARITY_THRESHOLDS["SILVER"]:
        return CardRarity.SILVER
    if percentile >= RARITY_THRESHOLDS["BRONZE"]:
        return CardRarity.BRONZE
    return CardRarity.COMMON


def calculate_rarity(overall_rating: int, rating_distribution) -> RarityResult:
    """Calcula mid-rank empírico conservando juntos todos los ratings empatados."""
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
    return RarityResult(
        overall_rating=overall_rating,
        percentile=percentile,
        rarity=rarity_from_percentile(percentile),
    )
