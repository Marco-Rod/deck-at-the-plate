"""
Modelos de snapshots de roster (CPU roster: plan V2 §12-§17)
============================================================
SourceTeamRosterSnapshot (quién estaba en el roster activo de una franquicia
REAL en una fecha) vs PlayerTeamStint (para qué equipo jugó este jugador).
Responsabilidades distintas: el CPU roster se deriva de snapshots + catálogo
publicado, nunca de Team.cards.

La capa SOURCE referencia SourceTeam (franquicia real). La capa GAME (Team)
es la que se expone públicamente.

Los snapshots son inmutables por fecha: nunca se sobrescribe uno anterior
(plan §43); reejecutar la misma fecha es idempotente vía UNIQUE.
"""

import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.core.time import utcnow


def _new_id() -> str:
    return str(uuid.uuid4())


class SourceTeamRosterSnapshot(Base):
    __tablename__ = "source_team_roster_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "source_team_id",
            "season",
            "as_of_date",
            "roster_type",
            name="uq_source_roster_snapshots_team_date_type",
        ),
        CheckConstraint("season >= 1900 AND season <= 2100", name="ck_source_roster_snapshots_season_range"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    source_team_id = Column(
        String(36), ForeignKey("source_teams.id"), nullable=False, index=True
    )
    season = Column(SmallInteger, nullable=False, index=True)
    as_of_date = Column(Date, nullable=False, index=True)
    # "ACTIVE" (26 man) / "40_MAN". V1 solo ACTIVE.
    roster_type = Column(String(20), nullable=False, default="ACTIVE", index=True)
    source = Column(String(30), nullable=False, default="MLB_STATS_API")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    members = relationship(
        "SourceTeamRosterMember", back_populates="snapshot", cascade="all, delete-orphan"
    )


class SourceTeamRosterMember(Base):
    __tablename__ = "source_team_roster_members"
    __table_args__ = (
        UniqueConstraint(
            "roster_snapshot_id", "player_id", name="uq_source_roster_members_snapshot_player"
        ),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    roster_snapshot_id = Column(
        String(36),
        ForeignKey("source_team_roster_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id = Column(String(36), ForeignKey("players.id", ondelete="RESTRICT"), nullable=False, index=True)
    # Códigos tal cual los devuelve MLB Stats API ("ACTIVE", "IL", "MINOR"...).
    status = Column(String(20), nullable=True)
    position = Column(String(5), nullable=True)
    jersey_number = Column(String(5), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    snapshot = relationship("SourceTeamRosterSnapshot", back_populates="members")
    player = relationship("Player")