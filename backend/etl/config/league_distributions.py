"""Configuración versionable de las distribuciones de métricas de pitcher."""

from dataclasses import dataclass


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


def default_distribution_version(season: int) -> str:
    return f"mlb-{season}-v1"
