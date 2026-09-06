"""
Capa SOURCE de equipos (plan V2 §10-§12, §36)
===============================================
SourceTeam: la franquicia real (MLB) tal cual existe en el mundo real,
identificada por (source, external_id). Jamás se expone en APIs públicas
(§35); la capa GAME es `Team` (franquicia pública UUID).

SourceTeamGameTeamMapping vincula una franquicia real con su franquicia
pública dentro de una ventana de validez. Solo puede haber una mapping
activa (valid_to IS NULL) por source_team.
"""
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.core.time import utcnow


def _new_id() -> str:
    return str(uuid.uuid4())


class SourceTeam(Base):
    __tablename__ = "source_teams"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_source_teams_source_external"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    source = Column(String(20), nullable=False, default="MLB")
    # Es el mlb_team_id de MLB Stats API (último valor en la transición de
    # abreviatura: LAA/108, NYM/121, etc.).
    external_id = Column(Integer, nullable=False)
    source_name = Column(String(120), nullable=False)
    source_abbreviation = Column(String(5), nullable=False, index=True)
    league = Column(String(10), nullable=False, default="MLB")
    division = Column(String(40), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    mappings = relationship(
        "SourceTeamGameTeamMapping",
        back_populates="source_team",
        cascade="all, delete-orphan",
    )


class SourceTeamGameTeamMapping(Base):
    __tablename__ = "source_team_game_team_mappings"
    __table_args__ = (
        UniqueConstraint(
            "source_team_id", "team_id", name="uq_source_team_game_team_mappings_pair"
        ),
        # Una sola mapping activa (valid_to NULL) por franquicia real.
        Index(
            "uq_source_team_game_team_mappings_active",
            "source_team_id",
            unique=True,
            postgresql_where=text("valid_to IS NULL"),
        ),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    source_team_id = Column(
        String(36),
        ForeignKey("source_teams.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    team_id = Column(
        String(36), ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    valid_from = Column(Date, nullable=False)
    valid_to = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    source_team = relationship("SourceTeam", back_populates="mappings")
    team = relationship("Team", backref="source_mappings")