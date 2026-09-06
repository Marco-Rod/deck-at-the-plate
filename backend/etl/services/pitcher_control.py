"""Calculadora auditable de Control para ratings-2.0, sin persistencia."""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.models import LeagueMetricDistribution, PitcherSeasonStats, Player, PlayerSeason
from etl.config.league_distributions import PITCHER_METRICS, default_distribution_version
from etl.config.ratings_2 import CONTROL_WEIGHTS, MIN_CONTROL_WEIGHT_COVERAGE, RATING_MODEL_VERSION
from etl.services.percentiles import distribution_percentile_rank, percentile_rating
from etl.services.rating_math import round_rating


@dataclass(frozen=True)
class ControlComponent:
    metric: str
    observed: float
    league_baseline: float
    sample_size: int
    stabilization: int
    shrinkage_weight: float
    adjusted: float
    percentile: float
    rating: int
    component_weight: float
    contribution: float


@dataclass(frozen=True)
class PitcherControlResult:
    mlb_id: int
    rating_model_version: str
    distribution_version: str
    rating: int | None
    weight_coverage: float
    components: list[ControlComponent] = field(default_factory=list)
    skipped_metrics: list[str] = field(default_factory=list)


def calculate_control_candidate(
    db: Session,
    *,
    mlb_id: int,
    season: int,
    data_start_date: date,
    data_end_date: date,
    distribution_version: str | None = None,
) -> PitcherControlResult:
    version = distribution_version or default_distribution_version()
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

    pending: list[tuple] = []
    skipped: list[str] = []
    for metric, component_weight in CONTROL_WEIGHTS.items():
        config = PITCHER_METRICS[metric]
        observed_value = getattr(pitcher, metric)
        sample_size = int(getattr(pitcher, config.sample_field))
        distribution = db.query(LeagueMetricDistribution).filter_by(
            season=season,
            role="PITCHER",
            metric=metric,
            pitch_type=None,
            pitch_family=None,
            distribution_version=version,
            data_start_date=data_start_date,
            data_end_date=data_end_date,
        ).one_or_none()
        if observed_value is None or sample_size <= 0 or distribution is None:
            skipped.append(metric)
            continue

        observed = float(observed_value)
        baseline = float(distribution.league_baseline)
        shrinkage_weight = sample_size / (sample_size + config.stabilization)
        adjusted = shrinkage_weight * observed + (1 - shrinkage_weight) * baseline
        percentile = distribution_percentile_rank(adjusted, distribution, direction=config.direction)
        component_rating = percentile_rating(percentile)
        pending.append((
            metric, observed, baseline, sample_size, config.stabilization,
            shrinkage_weight, adjusted, percentile, component_rating, component_weight,
        ))

    coverage = sum(item[-1] for item in pending)
    sufficient = coverage + 1e-12 >= MIN_CONTROL_WEIGHT_COVERAGE
    components = [
        ControlComponent(
            metric=metric,
            observed=observed,
            league_baseline=baseline,
            sample_size=sample_size,
            stabilization=stabilization,
            shrinkage_weight=shrinkage_weight,
            adjusted=adjusted,
            percentile=percentile,
            rating=component_rating,
            component_weight=component_weight,
            contribution=(component_rating * component_weight / coverage if sufficient else 0.0),
        )
        for (
            metric, observed, baseline, sample_size, stabilization,
            shrinkage_weight, adjusted, percentile, component_rating, component_weight,
        ) in pending
    ]
    rating = round_rating(sum(component.contribution for component in components)) if sufficient else None
    return PitcherControlResult(
        mlb_id=mlb_id,
        rating_model_version=RATING_MODEL_VERSION,
        distribution_version=version,
        rating=rating,
        weight_coverage=coverage,
        components=components,
        skipped_metrics=skipped,
    )
