"""Persistencia de metadata CORE (spec secciones 7, 8, 24 y checklist "Load").

Todos los upserts usan claves estables (mlb_id, team abbreviation y la ventana
de PlayerSeason); nunca se usa el nombre como identidad.
"""

import logging
from datetime import date
from sqlalchemy.orm import Session

from app.core.enums import Handedness, ThrowHand
from app.core.identities import game_team_id_for
from app.models import (
    GamePlayerIdentity,
    Player,
    PlayerSeason,
    PlayerTeamStint,
    SourceTeam,
    SourceTeamGameTeamMapping,
    SourceTeamRosterMember,
    SourceTeamRosterSnapshot,
    Team,
)
from etl.config.franchises import GameTeamConfig, load_game_franchises
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


def _franchise_config_for(record: TeamSourceRecord) -> GameTeamConfig | None:
    for config in load_game_franchises():
        if config.source_team_external_id == record.mlb_team_id:
            return config
    return None


def upsert_team(db: Session, record: TeamSourceRecord) -> Team:
    """Upsert de la franquicia GAME (plan V2 §10-§12).

    El id es determinístico (uuid5 de la abreviatura pública). El branding se
    toma de game_franchises.yaml cuando la franquicia real está configurada;
    en su defecto usa el nombre del record (mayormente para cargas previas).
    """
    team_id = game_team_id_for(record.abbreviation)
    if not record.abbreviation:
        raise ValueError("TeamSourceRecord sin abbreviation")
    team = db.get(Team, team_id)
    config = _franchise_config_for(record)
    if team is None:
        team = Team(
            id=team_id,
            abbreviation=record.abbreviation,
            name=config.name if config else record.name,
            city=config.city if config else record.location_name,
            slug=config.slug if config else record.abbreviation.lower(),
            primary_color=config.primary_color if config else "#121619",
            secondary_color=config.secondary_color if config else "#C5A059",
            is_cpu=config.is_cpu if config else True,
        )
        db.add(team)
        logger.info("team inserted id=%s name=%s", team_id, team.name)
    else:
        team.abbreviation = record.abbreviation
        if config:
            team.name = config.name
            team.city = config.city
            team.slug = config.slug
            team.primary_color = config.primary_color
            team.secondary_color = config.secondary_color
            team.is_cpu = config.is_cpu
        elif team.name != record.name:
            team.name = record.name
        if not config and record.location_name and team.city != record.location_name:
            team.city = record.location_name
        logger.info("team upserted id=%s", team_id)
    db.flush()
    return team


def upsert_source_team(db: Session, record: TeamSourceRecord) -> SourceTeam:
    """Upsert de la franquicia REAL por (source, external_id). Nunca expuesta."""
    source_team = (
        db.query(SourceTeam)
        .filter(
            SourceTeam.source == "MLB",
            SourceTeam.external_id == record.mlb_team_id,
        )
        .one_or_none()
    )
    if source_team is None:
        source_team = SourceTeam(
            source="MLB",
            external_id=record.mlb_team_id,
            source_name=record.name,
            source_abbreviation=record.abbreviation,
            league="MLB",
            is_active=record.active,
        )
        db.add(source_team)
        db.flush()
        logger.info("source_team inserted external_id=%s name=%s", record.mlb_team_id, record.name)
    else:
        source_team.source_name = record.name
        source_team.source_abbreviation = record.abbreviation
        source_team.is_active = record.active
        db.flush()
        logger.info("source_team upserted external_id=%s", record.mlb_team_id)
    return source_team


def upsert_game_team(db: Session, config: GameTeamConfig) -> Team:
    """Upsert de la franquicia GAME desde el config versionado (id estable)."""
    team = db.get(Team, config.game_team_id)
    if team is None:
        team = Team(
            id=config.game_team_id,
            abbreviation=config.public_abbreviation,
            name=config.name,
            city=config.city,
            slug=config.slug,
            primary_color=config.primary_color,
            secondary_color=config.secondary_color,
            is_cpu=config.is_cpu,
        )
        db.add(team)
        logger.info("game team inserted id=%s abbr=%s", config.game_team_id, config.public_abbreviation)
    else:
        team.abbreviation = config.public_abbreviation
        team.name = config.name
        team.city = config.city
        team.slug = config.slug
        team.primary_color = config.primary_color
        team.secondary_color = config.secondary_color
        team.is_cpu = config.is_cpu
        team.is_active = True
        logger.info("game team upserted id=%s abbr=%s", config.game_team_id, config.public_abbreviation)
    db.flush()
    return team


def upsert_source_game_mapping(
    db: Session,
    *,
    source_team: SourceTeam,
    team: Team,
    valid_from: date,
) -> SourceTeamGameTeamMapping:
    """Mapping activo SOURCE<->GAME; se cierra el anterior si apunta a otro team."""
    existing = (
        db.query(SourceTeamGameTeamMapping)
        .filter(
            SourceTeamGameTeamMapping.source_team_id == source_team.id,
            SourceTeamGameTeamMapping.valid_to.is_(None),
        )
        .one_or_none()
    )
    if existing is not None and existing.team_id == team.id:
        logger.info("mapping activo ya existe source=%s team=%s", source_team.id, team.id)
        return existing
    if existing is not None:
        # Rebranding: se cierra la mapping vigente antes de abrir la nueva.
        existing.valid_to = valid_from
        db.flush()

    mapping = (
        db.query(SourceTeamGameTeamMapping)
        .filter(
            SourceTeamGameTeamMapping.source_team_id == source_team.id,
            SourceTeamGameTeamMapping.team_id == team.id,
        )
        .one_or_none()
    )
    if mapping is None:
        mapping = SourceTeamGameTeamMapping(
            source_team_id=source_team.id,
            team_id=team.id,
            valid_from=valid_from,
        )
        db.add(mapping)
        logger.info("mapping inserted source=%s team=%s valid_from=%s", source_team.id, team.id, valid_from)
    else:
        mapping.valid_to = None
        logger.info("mapping reabierto source=%s team=%s", source_team.id, team.id)
    db.flush()
    return mapping


def upsert_game_player_identity(
    db: Session,
    *,
    player: Player,
    display_first_name: str,
    display_last_name: str,
    display_name: str,
    default_jersey_number: str | None = None,
    name_profile: str | None = None,
    generator_version: str | None = None,
) -> GamePlayerIdentity:
    identity = (
        db.query(GamePlayerIdentity)
        .filter(GamePlayerIdentity.player_id == player.id)
        .one_or_none()
    )
    if identity is None:
        identity = GamePlayerIdentity(
            player_id=player.id,
            display_first_name=display_first_name,
            display_last_name=display_last_name,
            display_name=display_name,
            default_jersey_number=default_jersey_number,
            name_profile=name_profile,
            generator_version=generator_version,
        )
        db.add(identity)
        db.flush()
        logger.info("game identity inserted player=%s name=%s", player.id, display_name)
    else:
        identity.display_first_name = display_first_name
        identity.display_last_name = display_last_name
        identity.display_name = display_name
        if default_jersey_number is not None:
            identity.default_jersey_number = default_jersey_number
        if name_profile is not None:
            identity.name_profile = name_profile
        if generator_version is not None:
            identity.generator_version = generator_version
        db.flush()
        logger.info("game identity upserted player=%s name=%s", player.id, display_name)
    return identity


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
    source_team_id: str,
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
            PlayerTeamStint.source_team_id == source_team_id,
            PlayerTeamStint.start_date == start_date,
        )
        .one_or_none()
    )
    if stint is None:
        stint = PlayerTeamStint(
            player_id=player.id,
            season=season,
            source_team_id=source_team_id,
            start_date=start_date,
            end_date=end_date,
            games=games,
            is_primary_at_cutoff=is_primary_at_cutoff,
        )
        db.add(stint)
        logger.info("stint inserted player=%s season=%s team=%s start=%s", player.id, season, source_team_id, start_date)
    else:
        stint.end_date = end_date
        stint.is_primary_at_cutoff = is_primary_at_cutoff
        logger.info("stint upserted player=%s season=%s team=%s", player.id, season, source_team_id)
    db.flush()
    return stint


def upsert_source_team_roster_snapshot(
    db: Session,
    *,
    source_team_id: str,
    season: int,
    as_of_date: date,
    roster_type: str = "ACTIVE",
    source: str = "MLB_STATS_API",
) -> SourceTeamRosterSnapshot:
    """Snapshot de roster idempotente por (source_team, season, as_of, type).

    Diferentes as_of_date generan snapshots distintos (historia), nunca se
    sobrescribe un snapshot anterior (plan §43).
    """
    snapshot = (
        db.query(SourceTeamRosterSnapshot)
        .filter(
            SourceTeamRosterSnapshot.source_team_id == source_team_id,
            SourceTeamRosterSnapshot.season == season,
            SourceTeamRosterSnapshot.as_of_date == as_of_date,
            SourceTeamRosterSnapshot.roster_type == roster_type,
        )
        .one_or_none()
    )
    if snapshot is None:
        snapshot = SourceTeamRosterSnapshot(
            source_team_id=source_team_id,
            season=season,
            as_of_date=as_of_date,
            roster_type=roster_type,
            source=source,
        )
        db.add(snapshot)
        db.flush()
        logger.info("roster snapshot inserted team=%s season=%s as_of=%s", source_team_id, season, as_of_date)
    return snapshot


def upsert_source_team_roster_member(
    db: Session,
    *,
    snapshot: SourceTeamRosterSnapshot,
    player: Player,
    status: str | None = None,
    position: str | None = None,
    jersey_number: str | None = None,
) -> SourceTeamRosterMember:
    member = (
        db.query(SourceTeamRosterMember)
        .filter(
            SourceTeamRosterMember.roster_snapshot_id == snapshot.id,
            SourceTeamRosterMember.player_id == player.id,
        )
        .one_or_none()
    )
    if member is None:
        member = SourceTeamRosterMember(
            roster_snapshot_id=snapshot.id,
            player_id=player.id,
            status=status,
            position=position,
            jersey_number=jersey_number,
        )
        db.add(member)
        logger.info("roster member inserted snapshot=%s player=%s", snapshot.id, player.id)
    else:
        member.status = status
        member.position = position
        member.jersey_number = jersey_number
        logger.info("roster member upserted snapshot=%s player=%s", snapshot.id, player.id)
    db.flush()
    return member