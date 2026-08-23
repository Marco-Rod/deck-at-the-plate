"""
Modelos de cartas del juego
============================
Define las dos entidades principales de cartas:
  - PlayerCardModel: Carta de jugador con atributos de bateo y/o pitcheo.
  - TacticCard: Carta táctica con efectos JSON aplicables durante el at-bat.

Convención de atributos en el modelo (inglés, columnas DB):
  Bateo  : contact, power
  Pitcheo: velocity, control, movement

El motor del juego (engine/) usa los mismos conceptos en español.
El módulo engine/attribute_mapper.py se encarga de la traducción.
"""
from sqlalchemy import Column, String, Integer, Boolean, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class CardRarity(str, enum.Enum):
    COMMON = "COMMON"
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    DIAMOND = "DIAMOND"


class PlayerCardModel(Base):
    __tablename__ = "player_cards"

    id = Column(String, primary_key=True, index=True)
    team_id = Column(String(3), ForeignKey("teams.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    number = Column(String, default="00")
    position = Column(String, nullable=False)  # "SP", "RP", "TWP", "DH", "CF", etc.
    overall = Column(Integer, nullable=False)   # 58 a 99
    rarity = Column(Enum(CardRarity), default=CardRarity.COMMON, nullable=False)

    # Flag para jugadores con atributos dobles (Bateo + Pitcheo)
    is_two_way = Column(Boolean, default=False)

    # Atributos de Bateo (0-99)
    power = Column(Integer, default=50)
    contact = Column(Integer, default=50)

    # Atributos de Pitcheo (0-99)
    velocity = Column(Integer, default=50)
    control = Column(Integer, default=50)
    movement = Column(Integer, default=50)  # Movimiento/quiebre del lanzamiento

    # Relaciones
    team = relationship("Team", back_populates="cards")
    inventories = relationship("UserCardInventory", back_populates="card")


class TacticCard(Base):
    __tablename__ = "tactic_cards"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # "BUFF", "DEBUFF", "INFO"
    target_role = Column(String, nullable=False)  # "BATTER", "PITCHER"
    effects = Column(JSON, nullable=False)
    description = Column(String, nullable=True)
