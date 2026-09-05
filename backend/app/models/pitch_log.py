"""
Modelo GAME TELEMETRY: PitchEventLog
====================================
Registra cada pitch resuelto por Deck at the Plate. Es la base para balancear
approaches, zonas, tácticas y versiones del Matchup Engine V1.

No reemplaza GameEventLog (box score del PA): lo complementa. La escritura del
log ocurre DESPUÉS de cerrar la resolución del pitch (nunca se almacenan
secretos ni la información del rival antes de resolver).
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from app.database import Base
from app.core.enums import BatterApproach, PitchFamily


def _new_id() -> str:
    return str(uuid.uuid4())


class PitchEventLog(Base):
    __tablename__ = "pitch_event_logs"
    __table_args__ = (
        UniqueConstraint(
            "game_id", "plate_appearance_id", "pitch_number",
            name="uq_pitch_event_logs_pa_pitch",
        ),
        CheckConstraint("pitch_number >= 1", name="ck_pitch_event_logs_pitch_number_min"),
        CheckConstraint("batter_zone_choice >= 1 AND batter_zone_choice <= 9", name="ck_pitch_event_logs_batter_zone"),
        CheckConstraint("pitcher_zone_choice >= 1 AND pitcher_zone_choice <= 9", name="ck_pitch_event_logs_pitcher_zone"),
        CheckConstraint("balls_before >= 0 AND balls_before <= 3", name="ck_pitch_event_logs_balls_before"),
        CheckConstraint("strikes_before >= 0 AND strikes_before <= 2", name="ck_pitch_event_logs_strikes_before"),
        CheckConstraint("outs_before >= 0 AND outs_before <= 2", name="ck_pitch_event_logs_outs_before"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    # game_id mantiene compatibilidad con GameSession.id; sin FK por sesiones históricas.
    game_id = Column(String, nullable=False, index=True)
    plate_appearance_id = Column(String(36), nullable=False, index=True)
    pitch_number = Column(SmallInteger, nullable=False)
    batter_card_id = Column(
        String, ForeignKey("player_cards.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    pitcher_card_id = Column(
        String, ForeignKey("player_cards.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Denormalización útil para analytics; nullable para legacy cards.
    batter_player_id = Column(String(36), ForeignKey("players.id"), nullable=True, index=True)
    pitcher_player_id = Column(String(36), ForeignKey("players.id"), nullable=True, index=True)
    batter_zone_choice = Column(SmallInteger, nullable=True)  # NULL cuando TAKE omite selección
    batter_approach = Column(
        Enum(BatterApproach, name="batterapproach", create_type=False),
        nullable=False,
        default=BatterApproach.REACT,
        index=True,
    )
    pitcher_zone_choice = Column(SmallInteger, nullable=False)
    pitch_type = Column(String(20), nullable=False, index=True)
    pitch_family = Column(
        Enum(PitchFamily, name="pitchfamily", create_type=False), nullable=False, index=True
    )
    zone_match = Column(Boolean, nullable=False, default=False, index=True)
    # NULL para REACT/TAKE donde no existe acierto binario.
    approach_match = Column(Boolean, nullable=True, index=True)
    balls_before = Column(SmallInteger, nullable=False, default=0)
    strikes_before = Column(SmallInteger, nullable=False, default=0)
    outs_before = Column(SmallInteger, nullable=False, default=0)
    pitcher_fatigue = Column(Numeric(7, 4), nullable=True)
    tactical_modifiers = Column(JSON, nullable=True)
    matchup_inputs = Column(JSON, nullable=True)
    # Distribución final antes del RNG (suma ≈ 1.0).
    probability_distribution = Column(JSON, nullable=False)
    rng_value = Column(Numeric(10, 9), nullable=True)
    result = Column(String(30), nullable=False, index=True)
    engine_version = Column(String(30), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)