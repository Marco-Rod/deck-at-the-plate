"""
Identidad pública del jugador (plan V2 §5-§9, §35)
===================================================
GamePlayerIdentity: la identidad GAME que verán los usuarios. Separa la
persona real (Player, con mlb_id) de su cara pública (display_*). Las APIs
públicas solo deben exponer estos campos, nunca el mlb_id ni el nombre real.
"""
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database import Base
from app.core.time import utcnow


def _new_id() -> str:
    return str(uuid.uuid4())


class GamePlayerIdentity(Base):
    __tablename__ = "game_player_identities"

    id = Column(String(36), primary_key=True, default=_new_id)
    player_id = Column(
        String(36),
        ForeignKey("players.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    display_first_name = Column(String(60), nullable=False)
    display_last_name = Column(String(60), nullable=False)
    display_name = Column(String(120), nullable=False, unique=True, index=True)  # §75: universo GAME sin caras duplicadas
    name_profile = Column(String(30), nullable=True)
    generator_version = Column(String(20), nullable=True)
    default_jersey_number = Column(String(5), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    player = relationship("Player", back_populates="game_identity")
    cards = relationship("PlayerCardModel", back_populates="game_identity")