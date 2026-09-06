"""Calculadora auditable de Contact para batter ratings-2.0, sin persistencia."""

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.models import BatterSeasonStats, LeagueMetricDistribution, Player, PlayerSeason
from etl.config.league_distributions import BATTER_METRICS, default_distribution_version
from etl.config.ratings_2 import (
    BATTER_CONTACT_STABILIZATIONS,
    BATTER_CONTACT_WEIGHTS,
    RATING_MODEL_VERSION,
)
from etl.services.percentiles import distribution_percentile_rank, percentile_rating
from etl.services.rating_math import round_rating


@dataclass(frozen=True)
class BatterContactComponent:
    metric: str
    distribution_id: str
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
class BatterContactRating:
    mlb_id: int
    rating_model_version: str
    distribution_version: str
    rating: int | None
    components: list[BatterContactComponent] = field(default_factory=list)
    skipped_metrics: list[str] = field(default_factory=list)


def calculate_batter_contact(
    db: Session,
    *,
    mlb_id: int,
    season: int,
    data_start_date: date,
    data_end_date: date,
    distribution_version: str | None = None,
) -> BatterContactRating:
    version = distribution_version or default_distribution_version()
    batter = (
        db.query(BatterSeasonStats)
        .join(PlayerSeason, PlayerSeason.id == BatterSeasonStats.player_season_id)
        .join(Player, Player.id == PlayerSeason.player_id)
        .filter(
            Player.mlb_id == mlb_id,
            PlayerSeason.season == season,
            PlayerSeason.data_start_date == data_start_date,
            PlayerSeason.data_end_date == data_end_date,
        )
        .one_or_none()
    )
    if batter is None:
        raise ValueError(f"sin BatterSeasonStats para mlb_id={mlb_id} en el snapshot solicitado")

    components: list[BatterContactComponent] = []
    skipped: list[str] = []
    for metric, component_weight in BATTER_CONTACT_WEIGHTS.items():
        config = BATTER_METRICS[metric]
        observed_value = getattr(batter, metric)
        sample_size = int(getattr(batter, config.sample_field))
        distribution = db.query(LeagueMetricDistribution).filter_by(
            season=season,
            role="BATTER",
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
        stabilization = BATTER_CONTACT_STABILIZATIONS[metric]
        shrinkage_weight = sample_size / (sample_size + stabilization)
        adjusted = shrinkage_weight * observed + (1 - shrinkage_weight) * baseline
        percentile = distribution_percentile_rank(
            adjusted, distribution, direction=config.direction
        )
        component_rating = percentile_rating(percentile)
        components.append(BatterContactComponent(
            metric=metric,
            distribution_id=distribution.id,
            observed=observed,
            league_baseline=baseline,
            sample_size=sample_size,
            stabilization=stabilization,
            shrinkage_weight=shrinkage_weight,
            adjusted=adjusted,
            percentile=percentile,
            rating=component_rating,
            component_weight=component_weight,
            contribution=component_rating * component_weight,
        ))

    rating = None
    if not skipped:
        rating = round_rating(sum(component.contribution for component in components))
    return BatterContactRating(
        mlb_id=mlb_id,
        rating_model_version=RATING_MODEL_VERSION,
        distribution_version=version,
        rating=rating,
        components=components,
        skipped_metrics=skipped,
    )
