"""Contexto versionado de una edición coleccionable de cartas."""

import enum
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Index,
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


class CardEditionType(str, enum.Enum):
    BASE = "BASE"
    TEAM_STAR = "TEAM_STAR"
    HOT_STREAK = "HOT_STREAK"
    MOMENT = "MOMENT"
    ALL_STAR = "ALL_STAR"
    MILESTONE = "MILESTONE"
    AWARD = "AWARD"
    POSTSEASON = "POSTSEASON"


class CardEditionSourceType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    GAME = "GAME"
    EVENT = "EVENT"
    MANUAL = "MANUAL"


class CardEdition(Base):
    """Describe qué representa una versión de carta, no su rarity ni ratings."""

    __tablename__ = "card_editions"
    __table_args__ = (
        UniqueConstraint(
            "season",
            "code",
            "version",
            name="uq_card_editions_season_code_version",
        ),
        CheckConstraint(
            "season >= 1900 AND season <= 2100",
            name="ck_card_editions_season",
        ),
        CheckConstraint(
            "length(trim(code)) > 0",
            name="ck_card_editions_code_nonempty",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_card_editions_name_nonempty",
        ),
        CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at",
            name="ck_card_editions_window",
        ),
        Index("ix_card_editions_type_active", "edition_type", "is_active"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    code = Column(String(80), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    edition_type = Column(
        Enum(
            CardEditionType,
            name="cardeditiontype",
            create_type=False,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    season = Column(SmallInteger, nullable=False, index=True)
    version = Column(String(40), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    source_type = Column(
        Enum(
            CardEditionSourceType,
            name="cardeditionsourcetype",
            create_type=False,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    source_reference = Column(String(255), nullable=True, index=True)
    starts_at = Column(DateTime(timezone=True), nullable=True, index=True)
    ends_at = Column(DateTime(timezone=True), nullable=True, index=True)
    # `metadata` es reservado por SQLAlchemy Declarative; el nombre físico sí
    # conserva el contrato de dominio solicitado.
    metadata_payload = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    cards = relationship("PlayerCardModel", back_populates="card_edition")
    rating_profiles = relationship("CardRatingProfile", back_populates="card_edition")
    moment_contexts = relationship("MomentContext", back_populates="card_edition")
