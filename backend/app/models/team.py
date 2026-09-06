from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Team(Base):
    """Franquicia pública (capa GAME, plan V2 §10-§12).

    id = UUID determinístico derivado de la abreviatura pública
    (uuid5, ver app/core/identities.py). Nunca expone datos SOURCE.
    """

    __tablename__ = "teams"

    id = Column(String(36), primary_key=True)
    # Abreviatura pública ("NYM"), usada como badge en la UI.
    abbreviation = Column(String(3), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    slug = Column(String(60), nullable=True, index=True)
    logo_asset = Column(String(120), nullable=True)
    primary_color = Column(String(7), nullable=False, default="#121619")
    secondary_color = Column(String(7), nullable=False, default="#C5A059")
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_cpu = Column(Boolean, nullable=False, default=False, index=True)  # Flag para equipos CPU vs Jugador

    # Relación con las cartas de jugadores pertenecientes a la franquicia
    cards = relationship("PlayerCardModel", back_populates="team")