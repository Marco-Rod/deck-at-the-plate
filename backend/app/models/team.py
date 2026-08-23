from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.database import Base

class Team(Base):
    __tablename__ = "teams"

    # ID de 3 letras estilo MLB ("LAD", "NYY", "BOS", etc.)
    id = Column(String(3), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    primary_color = Column(String(7), default="#121619")
    secondary_color = Column(String(7), default="#C5A059")

    # Relación con las cartas de jugadores pertenecientes a la franquicia
    cards = relationship("PlayerCardModel", back_populates="team")