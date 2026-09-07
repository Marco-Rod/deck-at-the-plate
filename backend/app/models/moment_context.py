"""Hechos observados que describen una edición MOMENT sin interpretarlos."""

import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.enums import enum_values
from app.core.time import utcnow
from app.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class MomentContextSourceType(str, enum.Enum):
    STATCAST = "STATCAST"
    MLB_STATS_API = "MLB_STATS_API"
    GAME = "GAME"
    EVENT = "EVENT"
    MANUAL = "MANUAL"


class MomentContext(Base):
    """Snapshot factual reproducible; no contiene evaluación ni boosts."""

    __tablename__ = "moment_contexts"
    __table_args__ = (
        UniqueConstraint(
            "player_id",
            "card_edition_id",
            "role",
            "context_version",
            name="uq_moment_contexts_identity",
        ),
        CheckConstraint(
            "role IN ('BATTER', 'PITCHER')", name="ck_moment_contexts_role"
        ),
        CheckConstraint(
            "season >= 1900 AND season <= 2100", name="ck_moment_contexts_season"
        ),
        CheckConstraint(
            "length(trim(source_reference)) > 0",
            name="ck_moment_contexts_source_reference_nonempty",
        ),
        CheckConstraint(
            "length(input_hash) = 64", name="ck_moment_contexts_input_hash"
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
    season = Column(SmallInteger, nullable=False, index=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)
    source_type = Column(
        Enum(
            MomentContextSourceType,
            name="momentcontextsourcetype",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
        index=True,
    )
    source_reference = Column(String(255), nullable=False, index=True)
    context_version = Column(String(40), nullable=False, index=True)
    facts = Column(JSON, nullable=False)
    input_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    player = relationship("Player")
    card_edition = relationship("CardEdition", back_populates="moment_contexts")
