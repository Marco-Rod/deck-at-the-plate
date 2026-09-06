"""Calculadora auditable de Velocity para ratings-2.0, sin persistencia."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import LeagueMetricDistribution, PitcherSeasonStats, Player, PlayerSeason
from etl.config.league_distributions import PITCHER_METRICS, default_distribution_version
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.percentiles import distribution_percentile_rank, percentile_rating


@dataclass(frozen=True)
class PitcherVelocityResult:
    mlb_id: int
    rating_model_version: str
    distribution_version: str
    rating: int | None
    observed: float | None
    league_baseline: float | None
    sample_size: int
    stabilization: int
    shrinkage_weight: float | None
    adjusted: float | None
    percentile: float | None
    unavailable_reason: str | None = None


def calculate_velocity_candidate(
    db: Session,
    *,
    mlb_id: int,
    season: int,
    data_start_date: date,
    data_end_date: date,
    distribution_version: str | None = None,
) -> PitcherVelocityResult:
    """Calcula Velocity con pitches como muestra provisional de ratings-2.0.

    Deuda conocida: reemplazar ``pitches`` por ``velocity_opportunities``
    cuando Analytics persista el número de release_speed válidos.
    """
    version = distribution_version or default_distribution_version()
    config = PITCHER_METRICS["avg_velocity"]
    pitcher = (
        db.query(PitcherSeasonStats)
        .join(PlayerSeason, PlayerSeason.id == PitcherSeasonStats.player_season_id)
        .join(Player, Player.id == PlayerSeason.player_id)
        .filter(
            Player.mlb_id == mlb_id,
            PlayerSeason.season == season,
            PlayerSeason.data_start_date == data_start_date,
            PlayerSeason.data_end_date == data_end_date,
        )
        .one_or_none()
    )
    if pitcher is None:
        raise ValueError(f"sin PitcherSeasonStats para mlb_id={mlb_id} en el snapshot solicitado")

    observed_value = pitcher.avg_velocity
    sample_size = int(getattr(pitcher, config.sample_field))
    distribution = db.query(LeagueMetricDistribution).filter_by(
        season=season,
        role="PITCHER",
        metric="avg_velocity",
        pitch_type=None,
        pitch_family=None,
        distribution_version=version,
        data_start_date=data_start_date,
        data_end_date=data_end_date,
    ).one_or_none()

    reason = None
    if observed_value is None:
        reason = "avg_velocity ausente"
    elif sample_size <= 0:
        reason = "muestra de velocity vacía"
    elif distribution is None:
        reason = "distribución avg_velocity ausente"
    if reason is not None:
        return PitcherVelocityResult(
            mlb_id=mlb_id, rating_model_version=RATING_MODEL_VERSION,
            distribution_version=version, rating=None,
            observed=float(observed_value) if observed_value is not None else None,
            league_baseline=None, sample_size=sample_size,
            stabilization=config.stabilization, shrinkage_weight=None,
            adjusted=None, percentile=None, unavailable_reason=reason,
        )

    observed = float(observed_value)
    baseline = float(distribution.league_baseline)
    weight = sample_size / (sample_size + config.stabilization)
    adjusted = weight * observed + (1 - weight) * baseline
    percentile = distribution_percentile_rank(adjusted, distribution, direction=config.direction)
    return PitcherVelocityResult(
        mlb_id=mlb_id, rating_model_version=RATING_MODEL_VERSION,
        distribution_version=version, rating=percentile_rating(percentile),
        observed=observed, league_baseline=baseline, sample_size=sample_size,
        stabilization=config.stabilization, shrinkage_weight=weight,
        adjusted=adjusted, percentile=percentile,
    )
