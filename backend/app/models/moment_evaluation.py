"""Interpretación versionada de un MomentContext, todavía sin tocar ratings."""

import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.enums import enum_values
from app.core.time import utcnow
from app.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class MomentType(str, enum.Enum):
    WALK_OFF_HR = "WALK_OFF_HR"
    MULTI_HR_GAME = "MULTI_HR_GAME"
    TEN_STRIKEOUT_GAME = "10_STRIKEOUT_GAME"


class MomentEvaluation(Base):
    """Scores interpretativos reproducibles separados de cualquier boost."""

    __tablename__ = "moment_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "moment_context_id",
            "evaluation_version",
            name="uq_moment_evaluations_identity",
        ),
        CheckConstraint(
            "significance_score >= 0 AND significance_score <= 1",
            name="ck_moment_evaluations_significance_score",
        ),
        CheckConstraint(
            "performance_score >= 0 AND performance_score <= 1",
            name="ck_moment_evaluations_performance_score",
        ),
        CheckConstraint(
            "leverage_score >= 0 AND leverage_score <= 1",
            name="ck_moment_evaluations_leverage_score",
        ),
        CheckConstraint(
            "statistical_uncommonness >= 0 AND statistical_uncommonness <= 1",
            name="ck_moment_evaluations_statistical_uncommonness",
        ),
        CheckConstraint(
            "length(input_hash) = 64", name="ck_moment_evaluations_input_hash"
        ),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    moment_context_id = Column(
        String(36),
        ForeignKey("moment_contexts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    moment_type = Column(
        Enum(
            MomentType,
            name="momenttype",
            create_type=False,
            values_callable=enum_values,
        ),
        nullable=False,
        index=True,
    )
    significance_score = Column(Numeric(6, 5), nullable=False)
    performance_score = Column(Numeric(6, 5), nullable=False)
    leverage_score = Column(Numeric(6, 5), nullable=False)
    statistical_uncommonness = Column(Numeric(6, 5), nullable=False)
    evaluation_version = Column(String(40), nullable=False, index=True)
    rules_payload = Column("rules", JSON, nullable=False)
    input_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    moment_context = relationship("MomentContext", back_populates="evaluations")
