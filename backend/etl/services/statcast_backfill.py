"""Backfill histórico de Statcast, separado de Analytics y Ratings."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import RawPitchEvent
from etl.services.statcast_population import (
    PopulationImportResult,
    import_statcast_population,
    select_population_players,
)
from etl.services.season_bounds import resolve_regular_season_start
from etl.sources.mlb import MLBStatsApiClient


@dataclass(frozen=True)
class StatcastBackfillResult:
    season: int
    role: str
    date_from: date
    date_to: date
    players_selected: int
    players_with_data: int
    players_without_data: int
    games: int
    pitches: int
    first_date: date | None
    last_date: date | None
    rows_inserted: int
    rows_updated: int
    rows_unchanged: int
    rows_rejected: int
    players_failed: int
    import_result: PopulationImportResult


def _coverage(
    db: Session,
    *,
    role: str,
    season: int,
    date_from: date,
    date_to: date,
    mlb_ids: list[int],
) -> tuple[int, int, date | None, date | None, int]:
    if not mlb_ids:
        return 0, 0, None, None, 0
    player_column = (
        RawPitchEvent.batter_mlb_id
        if role == "batter"
        else RawPitchEvent.pitcher_mlb_id
    )
    filters = (
        RawPitchEvent.season == season,
        RawPitchEvent.game_date >= date_from,
        RawPitchEvent.game_date <= date_to,
        player_column.in_(mlb_ids),
    )
    pitches, games, first_date, last_date = (
        db.query(
            func.count(RawPitchEvent.id),
            func.count(func.distinct(RawPitchEvent.game_pk)),
            func.min(RawPitchEvent.game_date),
            func.max(RawPitchEvent.game_date),
        )
        .filter(*filters)
        .one()
    )
    players_with_data = (
        db.query(func.count(func.distinct(player_column)))
        .filter(*filters)
        .scalar()
    )
    return int(pitches), int(games), first_date, last_date, int(players_with_data)


def backfill_statcast(
    db: Session,
    adapter,
    mlb_client: MLBStatsApiClient,
    *,
    season: int,
    role: str,
    date_to: date,
    limit: int | None = None,
    refresh: bool = False,
) -> StatcastBackfillResult:
    """Importa la población conocida desde el inicio regular hasta date_to."""
    normalized_role = role.lower()
    if normalized_role not in {"batter", "pitcher"}:
        raise ValueError("role debe ser batter o pitcher")
    date_from = resolve_regular_season_start(
        mlb_client, season=season, date_to=date_to
    )
    players = select_population_players(
        db, season=season, role=normalized_role, limit=limit
    )
    imported = import_statcast_population(
        db,
        adapter,
        season=season,
        role=normalized_role,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        refresh=refresh,
    )
    mlb_ids = [player.mlb_id for player in players]
    pitches, games, first_date, last_date, players_with_data = _coverage(
        db,
        role=normalized_role,
        season=season,
        date_from=date_from,
        date_to=date_to,
        mlb_ids=mlb_ids,
    )
    return StatcastBackfillResult(
        season=season,
        role=normalized_role,
        date_from=date_from,
        date_to=date_to,
        players_selected=len(players),
        players_with_data=players_with_data,
        players_without_data=len(players) - players_with_data,
        games=games,
        pitches=pitches,
        first_date=first_date,
        last_date=last_date,
        rows_inserted=imported.rows_inserted,
        rows_updated=imported.rows_updated,
        rows_unchanged=imported.rows_unchanged,
        rows_rejected=imported.rows_rejected,
        players_failed=imported.players_failed,
        import_result=imported,
    )
