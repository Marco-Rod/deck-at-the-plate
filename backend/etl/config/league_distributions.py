"""Configuración versionable de las distribuciones de métricas de pitcher."""

from dataclasses import dataclass


# Debe cambiar cuando cambien elegibilidad, estabilización, definición de
# métricas o algoritmo de percentiles. La temporada ya forma parte de la
# identidad de la distribución y no necesita codificarse aquí.
DISTRIBUTION_MODEL_VERSION = "dist-1.0"


@dataclass(frozen=True)
class MetricDistributionConfig:
    direction: str
    sample_field: str
    distribution_min_sample: int
    stabilization: int


PITCHER_METRICS = {
    "zone_rate": MetricDistributionConfig("higher", "zone_opportunities", 50, 200),
    "first_pitch_strike_rate": MetricDistributionConfig("higher", "first_pitch_opportunities", 15, 100),
    "walk_rate": MetricDistributionConfig("lower", "walk_opportunities", 15, 150),
    "strikeout_rate": MetricDistributionConfig("higher", "strikeout_opportunities", 15, 150),
    "hbp_rate": MetricDistributionConfig("lower", "hbp_opportunities", 15, 150),
    "csw_rate": MetricDistributionConfig("higher", "csw_opportunities", 50, 200),
}


def default_distribution_version() -> str:
    return DISTRIBUTION_MODEL_VERSION
