"""Contrato versionado de habilidades estadísticas completas por jugador."""

import uuid

from sqlalchemy import CheckConstraint, Column, Date, DateTime, ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.time import utcnow
from app.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


RATING_COLUMNS = (
    "contact_rating", "power_rating", "vision_rating", "clutch_rating",
    "velocity_rating", "control_rating", "movement_rating", "stuff_rating",
    "overall_rating",
)


class PlayerRatings(Base):
    """Resultado oficial completo para una metodología y referencia de liga."""

    __tablename__ = "player_ratings"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "season", "role", "rating_model_version",
            "distribution_version", "data_start_date", "data_end_date",
            name="uq_player_ratings_identity",
        ),
        # Clave candidata para que CardGenerationProfile pueda garantizar por
        # FK compuesta que el vínculo usa la misma rating_model_version.
        UniqueConstraint("id", "rating_model_version", name="uq_player_ratings_id_model_version"),
        CheckConstraint("season >= 1900 AND season <= 2100", name="ck_player_ratings_season"),
        CheckConstraint("data_end_date >= data_start_date", name="ck_player_ratings_window"),
        CheckConstraint("role IN ('BATTER', 'PITCHER')", name="ck_player_ratings_role"),
        CheckConstraint("length(input_hash) = 64", name="ck_player_ratings_input_hash"),
        CheckConstraint(
            "(role = 'BATTER' AND contact_rating IS NOT NULL AND power_rating IS NOT NULL "
            "AND vision_rating IS NOT NULL AND clutch_rating IS NOT NULL "
            "AND velocity_rating IS NULL AND control_rating IS NULL "
            "AND movement_rating IS NULL AND stuff_rating IS NULL) OR "
            "(role = 'PITCHER' AND velocity_rating IS NOT NULL AND control_rating IS NOT NULL "
            "AND movement_rating IS NOT NULL AND stuff_rating IS NOT NULL "
            "AND contact_rating IS NULL AND power_rating IS NULL "
            "AND vision_rating IS NULL AND clutch_rating IS NULL)",
            name="ck_player_ratings_complete_role_shape",
        ),
        *(
            CheckConstraint(
                f"{column} IS NULL OR ({column} >= 40 AND {column} <= 99)",
                name=f"ck_player_ratings_{column}_range",
            )
            for column in RATING_COLUMNS
        ),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    player_id = Column(String(36), ForeignKey("players.id", ondelete="RESTRICT"), nullable=False, index=True)
    season = Column(SmallInteger, nullable=False, index=True)
    role = Column(String(10), nullable=False, index=True)
    rating_model_version = Column(String(40), nullable=False, index=True)
    distribution_version = Column(String(40), nullable=False, index=True)
    data_start_date = Column(Date, nullable=False)
    data_end_date = Column(Date, nullable=False, index=True)

    contact_rating = Column(SmallInteger, nullable=True)
    power_rating = Column(SmallInteger, nullable=True)
    vision_rating = Column(SmallInteger, nullable=True)
    clutch_rating = Column(SmallInteger, nullable=True)
    velocity_rating = Column(SmallInteger, nullable=True)
    control_rating = Column(SmallInteger, nullable=True)
    movement_rating = Column(SmallInteger, nullable=True)
    stuff_rating = Column(SmallInteger, nullable=True)
    overall_rating = Column(SmallInteger, nullable=False)

    input_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    player = relationship("Player")
    card_generation_profiles = relationship("CardGenerationProfile", back_populates="player_ratings")
