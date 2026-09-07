"""Orquestación tolerante a fallos para importar una población Statcast."""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Player, PlayerSeason
from etl.pipelines.statcast import StatcastRawPipeline, StatcastRunResult


logger = logging.getLogger("etl.services.statcast_population")

PITCHER_POSITIONS = ("P", "SP", "RP", "SU", "CP", "CL", "TWP")
BATTER_POSITIONS = ("C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "TWP")


@dataclass(frozen=True)
class PopulationFailure:
    mlb_id: int
    error: str


@dataclass
class PopulationImportResult:
    players_selected: int = 0
    players_completed: int = 0
    players_no_data: int = 0
    players_failed: int = 0
    rows_extracted: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_unchanged: int = 0
    rows_rejected: int = 0
    failures: list[PopulationFailure] = field(default_factory=list)


def select_population_players(
    db: Session, *, season: int, role: str, limit: int | None
) -> list[Player]:
    """Selecciona una población SOURCE conocida, estable y sin duplicados."""
    if role not in {"batter", "pitcher"}:
        raise ValueError("role debe ser batter o pitcher")
    if limit is not None and limit < 1:
        raise ValueError("limit debe ser mayor que cero")

    season_players = select(PlayerSeason.player_id).where(PlayerSeason.season == season)
    query = db.query(Player).filter(
        Player.id.in_(season_players),
        Player.mlb_id.isnot(None),
        Player.primary_position.isnot(None),
    )
    if role == "pitcher":
        query = query.filter(Player.primary_position.in_(PITCHER_POSITIONS))
    else:
        # TWP es elegible en ambos roles; pitchers puros no están en esta lista.
        query = query.filter(Player.primary_position.in_(BATTER_POSITIONS))
    query = query.order_by(Player.mlb_id.asc())
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def import_statcast_population(
    db: Session,
    adapter,
    *,
    season: int,
    role: str,
    date_from: date,
    date_to: date,
    limit: int | None,
    refresh: bool = False,
    pipeline_factory: Callable = StatcastRawPipeline,
) -> PopulationImportResult:
    """Importa cada jugador de forma aislada y devuelve un resumen agregado."""
    if date_to < date_from:
        raise ValueError("date_to debe ser igual o posterior a date_from")
    players = select_population_players(db, season=season, role=role, limit=limit)
    result = PopulationImportResult(players_selected=len(players))

    for player in players:
        try:
            run: StatcastRunResult = pipeline_factory(db, adapter).run_player(
                mlb_id=player.mlb_id,
                role=role,
                date_from=date_from,
                date_to=date_to,
                season=season,
                refresh=refresh,
            )
        except Exception as exc:
            # run_player ya persiste su DataImportRun FAILED. El rollback deja la
            # sesión utilizable incluso si falla una implementación alternativa.
            db.rollback()
            result.players_failed += 1
            result.failures.append(PopulationFailure(player.mlb_id, str(exc)[:500]))
            logger.warning(
                "population %s falló mlb_id=%s error=%s", role, player.mlb_id, exc
            )
            continue

        result.rows_extracted += run.rows_extracted
        result.rows_inserted += run.rows_inserted
        result.rows_updated += run.rows_updated
        result.rows_unchanged += run.rows_unchanged
        result.rows_rejected += run.rows_rejected
        if run.rows_extracted == 0:
            result.players_no_data += 1
        else:
            result.players_completed += 1

    return result
