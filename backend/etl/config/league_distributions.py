"""Configuración versionable de distribuciones de métricas de liga."""

from dataclasses import dataclass


# Debe cambiar cuando cambien elegibilidad, estabilización, definición de
# métricas o algoritmo de percentiles. La temporada ya forma parte de la
# identidad de la distribución y no necesita codificarse aquí.
DISTRIBUTION_MODEL_VERSION = "dist-1.0"
MOVEMENT_PROFILE_MIN_PITCHES = 10
MOVEMENT_PITCH_TYPE_MIN_POPULATION = 10
MOVEMENT_FAMILY_MIN_POPULATION = 15
MOVEMENT_EXCLUDED_PITCH_TYPES = frozenset({"PO"})


@dataclass(frozen=True)
class MetricDistributionConfig:
    direction: str
    sample_field: str
    min_sample: int
    stabilization: int


@dataclass(frozen=True)
class BatterMetricDistributionConfig:
    """Contrato descriptivo; eligibility/shrinkage se calibrarán después."""

    direction: str
    sample_field: str


PITCHER_METRICS = {
    "zone_rate": MetricDistributionConfig("higher", "zone_opportunities", 50, 200),
    "first_pitch_strike_rate": MetricDistributionConfig("higher", "first_pitch_opportunities", 15, 100),
    "walk_rate": MetricDistributionConfig("lower", "walk_opportunities", 15, 150),
    "strikeout_rate": MetricDistributionConfig("higher", "strikeout_opportunities", 15, 150),
    "hbp_rate": MetricDistributionConfig("lower", "hbp_opportunities", 15, 150),
    "csw_rate": MetricDistributionConfig("higher", "csw_opportunities", 50, 200),
    "avg_velocity": MetricDistributionConfig("higher", "pitches", 50, 200),
    "whiff_rate": MetricDistributionConfig("higher", "swings", 20, 100),
}


BATTER_METRICS = {
    "contact_rate": BatterMetricDistributionConfig("higher", "swings"),
    "avg": BatterMetricDistributionConfig("higher", "ab"),
    "whiff_rate": BatterMetricDistributionConfig("lower", "swings"),
    "iso": BatterMetricDistributionConfig("higher", "ab"),
    "barrel_rate": BatterMetricDistributionConfig("higher", "barrel_opportunities"),
    "hard_hit_rate": BatterMetricDistributionConfig("higher", "hard_hit_opportunities"),
    "slg": BatterMetricDistributionConfig("higher", "ab"),
    "chase_rate": BatterMetricDistributionConfig("lower", "chase_opportunities"),
    "walk_rate": BatterMetricDistributionConfig("higher", "pa"),
    "strikeout_rate": BatterMetricDistributionConfig("lower", "pa"),
}


def default_distribution_version() -> str:
    return DISTRIBUTION_MODEL_VERSION
