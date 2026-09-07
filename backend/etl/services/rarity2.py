"""Compatibilidad legacy; el dominio canónico ahora es performance_tier2."""

from etl.services.performance_tier2 import (
    PerformanceTierResult,
    calculate_performance_tier,
    performance_tier_from_percentile,
)


RarityResult = PerformanceTierResult
rarity_from_percentile = performance_tier_from_percentile
calculate_rarity = calculate_performance_tier


__all__ = ["RarityResult", "calculate_rarity", "rarity_from_percentile"]
