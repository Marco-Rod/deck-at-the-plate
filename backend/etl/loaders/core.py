"""Persistencia de metadata CORE (spec secciones 7, 8, 24 y checklist "Load").

Todos los upserts usan claves estables (mlb_id, team abbreviation y la ventana
de PlayerSeason); nunca se usa el nombre como identidad.
"""

import logging
from datetime import date
from sqlalchemy.orm import Session

from app.core.enums import Handedness, ThrowHand
from app.models import Player, PlayerSeason, PlayerTeamStint, Team
from etl.dto import PlayerSourceRecord, TeamSourceRecord

logger = logging.getLogger("etl.loaders.core")


def _coerce_handedness(value: str | None) -> Handedness | None:
    if value is None:
        return None
    try:
        return Handedness(value)
    except ValueError:
        return None


def _coerce_throw_hand(value: str | None) -> ThrowHand | None:
    if value is None:
        return None
    try:
        return ThrowHand(value)
    except ValueError:
        return None


def upsert_team(db: Session, record: TeamSourceRecord) -> Team:
    team_id = record.abbreviation
    if not team_id:
        raise ValueError("TeamSourceRecord sin abbreviation")
    team = db.get(Team, team_id)
    if team is None:
        team = Team(
            id=team_id,
            name=record.name,
            city=record.location_name,
            is_cpu=True,
        )
        db.add(team)
        logger.info("team inserted id=%s name=%s", team_id, record.name)
    else:
        if team.name != record.name:
            team.name = record.name
        if record.location_name and team.city != record.location_name:
            team.city = record.location_name
        logger.info("team upserted id=%s", team_id)
    db.flush()
    return team


def upsert_player(db: Session, record: PlayerSourceRecord) -> Player:
    player = db.query(Player).filter(Player.mlb_id == record.mlb_id).one_or_none()
    if player is None:
        player = Player(
            mlb_id=record.mlb_id,
            full_name=record.full_name,
            first_name=record.first_name,
            last_name=record.last_name,
            birth_date=record.birth_date,
            primary_position=record.primary_position,
            bats=_coerce_handedness(record.bats),
            throws=_coerce_throw_hand(record.throws),
            is_active=record.is_active,
        )
        db.add(player)
        logger.info("player inserted mlb_id=%s name=%s", record.mlb_id, record.full_name)
    else:
        player.full_name = record.full_name
        player.first_name = record.first_name
        player.last_name = record.last_name
        if record.birth_date is not None:
            player.birth_date = record.birth_date
        if record.primary_position is not None:
            player.primary_position = record.primary_position
        if record.bats is not None:
            player.bats = _coerce_handedness(record.bats)
        if record.throws is not None:
            player.throws = _coerce_throw_hand(record.throws)
        player.is_active = record.is_active
        logger.info("player upserted mlb_id=%s", record.mlb_id)
    db.flush()
    return player


def upsert_player_season(
    db: Session,
    *,
    player: Player,
    season: int,
    data_start_date: date,
    data_end_date: date,
    import_run_id: str | None = None,
) -> PlayerSeason:
    ps = (
        db.query(PlayerSeason)
        .filter(
            PlayerSeason.player_id == player.id,
            PlayerSeason.season == season,
            PlayerSeason.data_start_date == data_start_date,
            PlayerSeason.data_end_date == data_end_date,
        )
        .one_or_none()
    )
    if ps is None:
        ps = PlayerSeason(
            player_id=player.id,
            season=season,
            data_start_date=data_start_date,
            data_end_date=data_end_date,
            import_run_id=import_run_id,
        )
        db.add(ps)
        db.flush()
        logger.info("player_season inserted player=%s season=%s", player.id, season)
    elif import_run_id is not None:
        ps.import_run_id = import_run_id
        db.flush()
    return ps


def get_player_season(
    db: Session,
    *,
    player: Player,
    season: int,
    data_start_date: date,
    data_end_date: date,
) -> PlayerSeason | None:
    return (
        db.query(PlayerSeason)
        .filter(
            PlayerSeason.player_id == player.id,
            PlayerSeason.season == season,
            PlayerSeason.data_start_date == data_start_date,
            PlayerSeason.data_end_date == data_end_date,
        )
        .one_or_none()
    )


def upsert_player_team_stint(
    db: Session,
    *,
    player: Player,
    season: int,
    team_id: str,
    start_date: date,
    end_date: date | None = None,
    games: int = 0,
    is_primary_at_cutoff: bool = False,
) -> PlayerTeamStint:
    stint = (
        db.query(PlayerTeamStint)
        .filter(
            PlayerTeamStint.player_id == player.id,
            PlayerTeamStint.season == season,
            PlayerTeamStint.team_id == team_id,
            PlayerTeamStint.start_date == start_date,
        )
        .one_or_none()
    )
    if stint is None:
        stint = PlayerTeamStint(
            player_id=player.id,
            season=season,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
            games=games,
            is_primary_at_cutoff=is_primary_at_cutoff,
        )
        db.add(stint)
        logger.info("stint inserted player=%s season=%s team=%s start=%s", player.id, season, team_id, start_date)
    else:
        stint.end_date = end_date
        stint.is_primary_at_cutoff = is_primary_at_cutoff
        logger.info("stint upserted player=%s season=%s team=%s", player.id, season, team_id)
    db.flush()
    return stint