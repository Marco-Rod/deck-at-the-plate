"""Generación tolerante a fallos de PlayerRatings para una población pitcher."""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

from sqlalchemy.orm import Session

from app.models import PitcherSeasonStats, Player, PlayerSeason
from etl.services.pitcher_ratings2 import calculate_pitcher_ratings2
from etl.services.player_ratings import persist_pitcher_ratings2


logger = logging.getLogger("etl.services.pitcher_ratings2_population")


@dataclass(frozen=True)
class PitcherRatings2PopulationFailure:
    mlb_id: int
    error: str


@dataclass
class PitcherRatings2PopulationResult:
    selected: int = 0
    completed: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    evidence_backfilled: int = 0
    skipped_incomplete: int = 0
    failed: int = 0
    failures: list[PitcherRatings2PopulationFailure] = field(default_factory=list)


def select_pitcher_ratings2_population(
    db: Session,
    *,
    season: int,
    data_start_date: date,
    data_end_date: date,
    limit: int | None = None,
) -> list[Player]:
    """Selecciona candidatos con Analytics pitcher en el snapshot exacto."""
    if data_end_date < data_start_date:
        raise ValueError("data_end_date debe ser igual o posterior a data_start_date")
    if limit is not None and limit < 1:
        raise ValueError("limit debe ser mayor que cero")
    query = (
        db.query(Player)
        .join(PlayerSeason, PlayerSeason.player_id == Player.id)
        .join(PitcherSeasonStats, PitcherSeasonStats.player_season_id == PlayerSeason.id)
        .filter(
            PlayerSeason.season == season,
            PlayerSeason.data_start_date == data_start_date,
            PlayerSeason.data_end_date == data_end_date,
            Player.mlb_id.isnot(None),
        )
        .order_by(Player.mlb_id.asc())
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def generate_pitcher_ratings2_population(
    db: Session,
    *,
    season: int,
    data_start_date: date,
    data_end_date: date,
    distribution_version: str | None = None,
    limit: int | None = None,
    calculator: Callable = calculate_pitcher_ratings2,
    persister: Callable = persist_pitcher_ratings2,
) -> PitcherRatings2PopulationResult:
    """Calcula y persiste cada candidato sin abortar el batch por un jugador."""
    players = select_pitcher_ratings2_population(
        db,
        season=season,
        data_start_date=data_start_date,
        data_end_date=data_end_date,
        limit=limit,
    )
    result = PitcherRatings2PopulationResult(selected=len(players))
    for player in players:
        try:
            ratings = calculator(
                db,
                mlb_id=player.mlb_id,
                season=season,
                data_start_date=data_start_date,
                data_end_date=data_end_date,
                distribution_version=distribution_version,
            )
            component_ratings = (
                ratings.velocity.rating,
                ratings.control.rating,
                ratings.movement.rating,
                ratings.stuff.rating,
            )
            if ratings.overall is None or any(value is None for value in component_ratings):
                result.skipped_incomplete += 1
                continue
            persisted = persister(
                db,
                ratings,
                season=season,
                data_start_date=data_start_date,
                data_end_date=data_end_date,
            )
            status = persisted.status.lower()
            if status not in {"created", "updated", "unchanged", "evidence_backfilled"}:
                raise RuntimeError(f"estado de persistencia inesperado: {persisted.status}")
            setattr(result, status, getattr(result, status) + 1)
            result.completed += 1
        except Exception as exc:
            db.rollback()
            result.failed += 1
            result.failures.append(
                PitcherRatings2PopulationFailure(player.mlb_id, str(exc)[:500])
            )
            logger.exception(
                "pitcher ratings-2.0 population falló mlb_id=%s", player.mlb_id
            )
    return result
