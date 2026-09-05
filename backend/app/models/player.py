"""
Modelos CORE de identidad del pelotero real
===========================================
Player / PlayerSeason / PlayerTeamStint.

Separan la identidad del jugador (fuente maestra) de la carta jugable
(PlayerCardModel). Una fila por persona, independiente de temporada y equipo.

Convenciones (ver referencias/nuevos_modelos.docx):
    - IDs internos: String UUID.
    - IDs MLB: enteros, unique/indexados (clave estable con fuentes MLB/Statcast).
    - Fechas: Date para cobertura; DateTime(timezone=True) para timestamps operativos.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from app.database import Base
from app.core.enums import Handedness, ThrowHand


def _new_id() -> str:
    return str(uuid.uuid4())


class Player(Base):
    """Fuente maestra de identidad del pelotero real. Nunca borrar históricos."""

    __tablename__ = "players"

    id = Column(String(36), primary_key=True, default=_new_id)
    mlb_id = Column(Integer, nullable=False, unique=True, index=True)
    full_name = Column(String(120), nullable=False, index=True)
    first_name = Column(String(60), nullable=True)
    last_name = Column(String(60), nullable=True, index=True)
    birth_date = Column(Date, nullable=True)
    # Código MLB/game: SP, RP, C, 1B, etc. Actual/general, puede variar por temporada.
    primary_position = Column(String(5), nullable=True, index=True)
    bats = Column(Enum(Handedness, name="handedness", create_type=False), nullable=True, index=True)
    throws = Column(Enum(ThrowHand, name="throwhand", create_type=False), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PlayerSeason(Base):
    """Snapshot lógico de un jugador en una temporada y ventana de datos.

    Permite representar "2026 hasta 31-ago" sin fingir que la temporada estaba completa.
    """

    __tablename__ = "player_seasons"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "season",
            "data_start_date",
            "data_end_date",
            name="uq_player_seasons_player_season_window",
        ),
        CheckConstraint("season >= 1900 AND season <= 2100", name="ck_player_seasons_season_range"),
        CheckConstraint("data_end_date >= data_start_date", name="ck_player_seasons_date_window"),
        CheckConstraint("games >= 0", name="ck_player_seasons_games_non_negative"),
        CheckConstraint("plate_appearances >= 0", name="ck_player_seasons_pa_non_negative"),
        CheckConstraint("batters_faced >= 0", name="ck_player_seasons_bf_non_negative"),
        CheckConstraint("outs_recorded >= 0", name="ck_player_seasons_outs_non_negative"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    player_id = Column(
        String(36), ForeignKey("players.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    season = Column(SmallInteger, nullable=False, index=True)
    data_start_date = Column(Date, nullable=False)
    data_end_date = Column(Date, nullable=False, index=True)
    is_complete = Column(Boolean, nullable=False, default=False, index=True)
    games = Column(Integer, nullable=False, default=0)
    plate_appearances = Column(Integer, nullable=False, default=0)
    batters_faced = Column(Integer, nullable=False, default=0)
    outs_recorded = Column(Integer, nullable=False, default=0)
    # IP = outs_recorded / 3. Se prefieren outs para evitar decimales.
    import_run_id = Column(String(36), ForeignKey("data_import_runs.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PlayerTeamStint(Base):
    """Afiliación de un jugador a un equipo dentro de una temporada.

    Evita modelar player_season.team_id como si un jugador nunca fuera traspasado.
    """

    __tablename__ = "player_team_stints"
    __table_args__ = (
        CheckConstraint("games >= 0", name="ck_player_team_stints_games_non_negative"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    player_id = Column(
        String(36), ForeignKey("players.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    season = Column(SmallInteger, nullable=False, index=True)
    team_id = Column(String(3), ForeignKey("teams.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=True)
    # NULL significa que sigue activo al corte.
    end_date = Column(Date, nullable=True)
    games = Column(Integer, nullable=False, default=0)
    is_primary_at_cutoff = Column(Boolean, nullable=False, default=False, index=True)