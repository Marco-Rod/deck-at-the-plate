"""
Modelo CARD GENERATION: CardGenerationProfile
=============================================
Snapshot INMUTABLE de cómo un perfil estadístico se convirtió en ratings
jugables. Permite regenerar cartas, comparar algoritmos y explicar cada valor.

Rules:
    - Es inmutable (no onupdate). Crear una nueva carta; nunca mutar una carta
      ya poseída cuando cambia el rating model.
    - rating_model_version identifica el algoritmo; nunca reutilizar la misma
      versión con fórmulas diferentes.
    - La fórmula de ratings vive FUERA del modelo (en el pipeline ETL/ETL),
      versionada. Este modelo solo persiste el resultado + metadata.
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    JSON,
    SmallInteger,
    String,
    UniqueConstraint,
)
from app.database import Base
from app.models.card import CardRarity


def _new_id() -> str:
    return str(uuid.uuid4())


class CardGenerationProfile(Base):
    __tablename__ = "card_generation_profiles"
    __table_args__ = (
        UniqueConstraint(
            "player_season_id", "rating_model_version",
            name="uq_card_generation_profiles_season_version",
        ),
        CheckConstraint("contact_rating >= 0 AND contact_rating <= 99", name="ck_card_generation_contact"),
        CheckConstraint("power_rating >= 0 AND power_rating <= 99", name="ck_card_generation_power"),
        CheckConstraint("vision_rating >= 0 AND vision_rating <= 99", name="ck_card_generation_vision"),
        CheckConstraint("clutch_rating >= 0 AND clutch_rating <= 99", name="ck_card_generation_clutch"),
        CheckConstraint("velocity_rating >= 0 AND velocity_rating <= 99", name="ck_card_generation_velocity"),
        CheckConstraint("control_rating >= 0 AND control_rating <= 99", name="ck_card_generation_control"),
        CheckConstraint("movement_rating >= 0 AND movement_rating <= 99", name="ck_card_generation_movement"),
        CheckConstraint("overall_rating >= 0 AND overall_rating <= 99", name="ck_card_generation_overall"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    player_season_id = Column(
        String(36), ForeignKey("player_seasons.id"), nullable=False, index=True
    )
    rating_model_version = Column(String(30), nullable=False, index=True)
    contact_rating = Column(SmallInteger, nullable=False)
    power_rating = Column(SmallInteger, nullable=False)
    vision_rating = Column(SmallInteger, nullable=False)
    clutch_rating = Column(SmallInteger, nullable=False)
    velocity_rating = Column(SmallInteger, nullable=False, default=0)
    control_rating = Column(SmallInteger, nullable=False, default=0)
    movement_rating = Column(SmallInteger, nullable=False, default=0)
    overall_rating = Column(SmallInteger, nullable=False)
    calculated_rarity = Column(
        # Reutilizamos el enum ya existente en el proyecto (no duplicar).
        Enum(CardRarity, name="cardrarity", create_type=False),
        nullable=False,
        default=CardRarity.COMMON,
        index=True,
    )
    primary_batter_trait = Column(String(40), nullable=True, index=True)
    primary_pitcher_trait = Column(String(40), nullable=True, index=True)
    # Repertoire ya transformado al contrato del juego (máx. 4 pitches).
    repertoire_payload = Column(JSON, nullable=True)
    # Percentiles/inputs/parámetros suficientes para explicar el cálculo.
    calculation_metadata = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)