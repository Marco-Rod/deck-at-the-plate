"""Ratings jugables de una carta concreta dentro de una edición."""

import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    JSON,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.time import utcnow
from app.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


RATING_COLUMNS = (
    "contact_rating",
    "power_rating",
    "vision_rating",
    "clutch_rating",
    "velocity_rating",
    "control_rating",
    "movement_rating",
    "stuff_rating",
    "overall_rating",
)


class CardRatingProfile(Base):
    """Separa los ratings de la carta de la evaluación estadística base."""

    __tablename__ = "card_rating_profiles"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "card_edition_id",
            "role",
            "rating_policy_version",
            name="uq_card_rating_profiles_identity",
        ),
        ForeignKeyConstraint(
            ["source_player_ratings_id", "player_id", "role"],
            ["player_ratings.id", "player_ratings.player_id", "player_ratings.role"],
            name="fk_card_rating_profiles_source_player_role",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "role IN ('BATTER', 'PITCHER')",
            name="ck_card_rating_profiles_role",
        ),
        CheckConstraint(
            "length(input_hash) = 64",
            name="ck_card_rating_profiles_input_hash",
        ),
        CheckConstraint(
            "(role = 'BATTER' AND contact_rating IS NOT NULL "
            "AND power_rating IS NOT NULL AND vision_rating IS NOT NULL "
            "AND clutch_rating IS NOT NULL AND velocity_rating IS NULL "
            "AND control_rating IS NULL AND movement_rating IS NULL "
            "AND stuff_rating IS NULL) OR "
            "(role = 'PITCHER' AND velocity_rating IS NOT NULL "
            "AND control_rating IS NOT NULL AND movement_rating IS NOT NULL "
            "AND stuff_rating IS NOT NULL AND contact_rating IS NULL "
            "AND power_rating IS NULL AND vision_rating IS NULL "
            "AND clutch_rating IS NULL)",
            name="ck_card_rating_profiles_complete_role_shape",
        ),
        *(
            CheckConstraint(
                f"{column} IS NULL OR ({column} >= 40 AND {column} <= 99)",
                name=f"ck_card_rating_profiles_{column}_range",
            )
            for column in RATING_COLUMNS
        ),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    player_id = Column(
        String(36), ForeignKey("players.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    card_edition_id = Column(
        String(36),
        ForeignKey("card_editions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role = Column(String(10), nullable=False, index=True)
    contact_rating = Column(SmallInteger, nullable=True)
    power_rating = Column(SmallInteger, nullable=True)
    vision_rating = Column(SmallInteger, nullable=True)
    clutch_rating = Column(SmallInteger, nullable=True)
    velocity_rating = Column(SmallInteger, nullable=True)
    control_rating = Column(SmallInteger, nullable=True)
    movement_rating = Column(SmallInteger, nullable=True)
    stuff_rating = Column(SmallInteger, nullable=True)
    overall_rating = Column(SmallInteger, nullable=False)
    source_player_ratings_id = Column(String(36), nullable=False, index=True)
    rating_policy_version = Column(String(40), nullable=False, index=True)
    input_hash = Column(String(64), nullable=False, index=True)
    metadata_payload = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    player = relationship("Player")
    card_edition = relationship("CardEdition", back_populates="rating_profiles")
    source_player_ratings = relationship("PlayerRatings", overlaps="player")
