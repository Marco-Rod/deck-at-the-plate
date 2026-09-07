"""Orquesta snapshots season-to-date de PlayerRatings hasta una fecha dada."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import RawPitchEvent
from etl.pipelines.analytics import AnalyticsPipeline, AnalyticsRunResult
from etl.services.batter_ratings2_population import (
    BatterRatings2PopulationResult,
    generate_batter_ratings2_population,
)
from etl.services.league_distributions import (
    DistributionBuildResult,
    build_league_distributions,
)
from etl.services.pitcher_ratings2_population import (
    PitcherRatings2PopulationResult,
    generate_pitcher_ratings2_population,
)


@dataclass(frozen=True)
class PlayerRatingsAsOfResult:
    season: int
    role: str
    data_start_date: date
    data_end_date: date
    analytics: AnalyticsRunResult
    distributions: DistributionBuildResult
    ratings: BatterRatings2PopulationResult | PitcherRatings2PopulationResult


def _require_raw_data(
    db: Session, *, season: int, data_start_date: date, data_end_date: date
) -> None:
    exists = (
        db.query(RawPitchEvent.id)
        .filter(
            RawPitchEvent.season == season,
            RawPitchEvent.game_date >= data_start_date,
            RawPitchEvent.game_date <= data_end_date,
        )
        .first()
    )
    if exists is None:
        raise ValueError(
            "sin RawPitchEvent para el snapshot season-to-date solicitado; "
            "ingiere primero la historia hasta as_of_date"
        )


def generate_player_ratings_as_of(
    db: Session,
    *,
    season: int,
    role: str,
    as_of_date: date,
    distribution_version: str | None = None,
    limit: int | None = None,
) -> PlayerRatingsAsOfResult:
    """Construye Analytics, distribuciones y ratings desde enero 1 hasta as-of."""
    normalized_role = role.upper()
    if normalized_role not in {"BATTER", "PITCHER"}:
        raise ValueError("role debe ser batter o pitcher")
    if as_of_date.year != season:
        raise ValueError("as_of_date debe pertenecer a season")
    if limit is not None and limit < 1:
        raise ValueError("limit debe ser mayor que cero")

    data_start_date = date(season, 1, 1)
    _require_raw_data(
        db,
        season=season,
        data_start_date=data_start_date,
        data_end_date=as_of_date,
    )
    analytics = AnalyticsPipeline(db).rebuild(
        season=season,
        data_start_date=data_start_date,
        data_end_date=as_of_date,
    )
    distributions = build_league_distributions(
        db,
        season=season,
        role=normalized_role,
        data_start_date=data_start_date,
        data_end_date=as_of_date,
        distribution_version=distribution_version,
    )
    population_builder = (
        generate_batter_ratings2_population
        if normalized_role == "BATTER"
        else generate_pitcher_ratings2_population
    )
    ratings = population_builder(
        db,
        season=season,
        data_start_date=data_start_date,
        data_end_date=as_of_date,
        distribution_version=distribution_version,
        limit=limit,
    )
    return PlayerRatingsAsOfResult(
        season=season,
        role=normalized_role,
        data_start_date=data_start_date,
        data_end_date=as_of_date,
        analytics=analytics,
        distributions=distributions,
        ratings=ratings,
    )
