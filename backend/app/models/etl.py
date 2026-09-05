"""
Modelos de auditoría y datos RAW del ETL
=========================================
DataImportRun / RawPitchEvent.

- DataImportRun traza cada ejecución de extracción/carga (cargas reproducibles).
- RawPitchEvent representa un lanzamiento real normalizado desde Statcast. Es
  el origen reproducible de los agregados, pero NUNCA se consulta durante un
  turno del juego (el Matchup Engine consume perfiles derivados).

Idempotencia: el ETL debe reejecutar la misma ventana sin duplicados, por eso
raw_pitch_events tiene UNIQUE (game_pk, at_bat_number, pitch_number).
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from app.database import Base
from app.core.enums import Handedness, ImportStatus, PitchFamily, ThrowHand


def _new_id() -> str:
    return str(uuid.uuid4())


class DataImportRun(Base):
    """Traza de una ejecución de extracción/carga/transformación."""

    __tablename__ = "data_import_runs"

    id = Column(String(36), primary_key=True, default=_new_id)
    source = Column(String(30), nullable=False, index=True)  # STATCAST, MLB_STATS_API
    pipeline_version = Column(String(30), nullable=False, index=True)
    season = Column(SmallInteger, nullable=True, index=True)
    date_from = Column(Date, nullable=True)
    date_to = Column(Date, nullable=True)
    status = Column(
        Enum(ImportStatus, name="importstatus", create_type=False),
        nullable=False,
        default=ImportStatus.RUNNING,
        index=True,
    )
    rows_extracted = Column(Integer, nullable=False, default=0)
    rows_inserted = Column(Integer, nullable=False, default=0)
    rows_updated = Column(Integer, nullable=False, default=0)
    rows_rejected = Column(Integer, nullable=False, default=0)
    error_summary = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class RawPitchEvent(Base):
    """Un lanzamiento real normalizado desde Statcast. Origen reproducible de análisis."""

    __tablename__ = "raw_pitch_events"
    __table_args__ = (
        UniqueConstraint(
            "game_pk", "at_bat_number", "pitch_number", name="uq_raw_pitch_events_unique_pitch"
        ),
        CheckConstraint("balls >= 0 AND balls <= 3", name="ck_raw_pitch_events_balls_range"),
        CheckConstraint("strikes >= 0 AND strikes <= 2", name="ck_raw_pitch_events_strikes_range"),
        CheckConstraint("outs_when_up >= 0 AND outs_when_up <= 2", name="ck_raw_pitch_events_outs_range"),
        CheckConstraint("inning >= 1", name="ck_raw_pitch_events_inning_min"),
        CheckConstraint("game_zone >= 1 AND game_zone <= 9", name="ck_raw_pitch_events_game_zone_range"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    import_run_id = Column(
        String(36), ForeignKey("data_import_runs.id"), nullable=False, index=True
    )
    source = Column(String(30), nullable=False, default="STATCAST", index=True)
    game_pk = Column(BigInteger, nullable=False, index=True)
    game_date = Column(Date, nullable=False, index=True)
    season = Column(SmallInteger, nullable=False, index=True)
    at_bat_number = Column(Integer, nullable=False)
    pitch_number = Column(SmallInteger, nullable=False)
    batter_mlb_id = Column(Integer, nullable=False, index=True)
    pitcher_mlb_id = Column(Integer, nullable=False, index=True)
    stand = Column(Enum(Handedness, name="handedness", create_type=False), nullable=True, index=True)
    p_throws = Column(Enum(ThrowHand, name="throwhand", create_type=False), nullable=True, index=True)
    balls = Column(SmallInteger, nullable=True)
    strikes = Column(SmallInteger, nullable=True)
    outs_when_up = Column(SmallInteger, nullable=True)
    inning = Column(SmallInteger, nullable=True)
    inning_topbot = Column(String(3), nullable=True)
    pitch_type = Column(String(12), nullable=True, index=True)
    pitch_family = Column(
        Enum(PitchFamily, name="pitchfamily", create_type=False), nullable=True, index=True
    )
    release_speed = Column(Numeric(5, 2), nullable=True)  # mph
    release_spin_rate = Column(Numeric(7, 2), nullable=True)  # rpm
    pfx_x = Column(Numeric(7, 4), nullable=True)
    pfx_z = Column(Numeric(7, 4), nullable=True)
    plate_x = Column(Numeric(7, 4), nullable=True)
    plate_z = Column(Numeric(7, 4), nullable=True)
    statcast_zone = Column(SmallInteger, nullable=True, index=True)
    game_zone = Column(SmallInteger, nullable=True, index=True)
    description = Column(String(50), nullable=True, index=True)
    event = Column(String(50), nullable=True, index=True)
    bb_type = Column(String(20), nullable=True)
    launch_speed = Column(Numeric(5, 2), nullable=True)
    launch_angle = Column(Numeric(6, 2), nullable=True)
    estimated_woba = Column(Numeric(6, 5), nullable=True)
    woba_value = Column(Numeric(6, 5), nullable=True)
    home_team = Column(String(3), nullable=True, index=True)
    away_team = Column(String(3), nullable=True, index=True)
    raw_payload_hash = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)