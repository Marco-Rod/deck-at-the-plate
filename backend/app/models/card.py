"""
Modelos de cartas del juego
============================
Define las dos entidades principales de cartas:
  - PlayerCardModel: Carta de jugador con atributos de bateo y/o pitcheo y su repertorio.
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
from app.core.enums import PITCHER_POSITIONS


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

    # Flag para jugadores con atributos dobles (Bateo + Pitcheo, ej. Shohei Ohtani)
    is_two_way = Column(Boolean, default=False)

    # Atributos de Bateo (0-99)
    power = Column(Integer, default=50)
    contact = Column(Integer, default=50)

    # Atributos de Pitcheo (0-99)
    velocity = Column(Integer, default=50)
    control = Column(Integer, default=50)
    movement = Column(Integer, default=50)  # Movimiento/quiebre del lanzamiento

    # Repertorio de pitcheos (Solo para pitchers y two-way players)
    # Estructura JSON guardada en DB:
    # [
    #   {"pitch_type": "4-SEAM", "velocity": 96, "control": 92, "movement": 88},
    #   {"pitch_type": "SLIDER", "velocity": 85, "control": 88, "movement": 94},
    #   {"pitch_type": "CURVE", "velocity": 78, "control": 80, "movement": 90}
    # ]
    repertoire = Column(JSON, nullable=True, default=list)

    # Relaciones
    team = relationship("Team", back_populates="cards")
    inventories = relationship("UserCardInventory", back_populates="card")

    @property
    def is_pitcher(self) -> bool:
        """Determina si la carta puede lanzar en el juego."""
        return self.position in PITCHER_POSITIONS or self.is_two_way

    @property
    def is_batter(self) -> bool:
        """Determina si la carta puede batear en el juego."""
        return self.position not in PITCHER_POSITIONS or self.is_two_way

    def get_pitch_stats(self, pitch_type_name: str) -> dict | None:
        """
        Retorna las estadísticas individuales de un picheo específico del repertorio.
        Si es IBB (Base intencional) otorga un objeto por defecto.
        """
        if pitch_type_name == "IBB":
            return {"pitch_type": "IBB", "velocity": 60, "control": 99, "movement": 0}

        if not self.repertoire:
            return None

        for pitch in self.repertoire:
            if pitch.get("pitch_type") == pitch_type_name:
                return pitch
        return None
    
    def validate_repertoire(self) -> bool:
        """
        Valida que el repertorio no tenga más de 4 pitcheos únicos.
        Retorna True si es válido, False si excede el límite.
        """
        if not self.repertoire:
            return True
        
        # Limitar a máximo 4 pitcheos únicos
        if len(self.repertoire) > 4:
            return False
        
        # Verificar que no hay duplicados
        pitch_types = [p.get("pitch_type") for p in self.repertoire]
        return len(pitch_types) == len(set(pitch_types))

    @staticmethod
    def get_rarity_by_overall(overall: int) -> "CardRarity":
        """
        Asigna rareza automáticamente basada en el overall del jugador.
        
        Mapeo:
        - 90-99: DIAMOND (Élite)
        - 85-89: GOLD (Estelar)
        - 80-84: SILVER (Muy Bueno)
        - 75-79: BRONZE (Bueno)
        - < 75: COMMON (Base)
        """
        if overall >= 90:
            return CardRarity.DIAMOND
        elif overall >= 85:
            return CardRarity.GOLD
        elif overall >= 80:
            return CardRarity.SILVER
        elif overall >= 75:
            return CardRarity.BRONZE
        else:
            return CardRarity.COMMON


class TacticCard(Base):
    __tablename__ = "tactic_cards"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # "BUFF", "DEBUFF", "INFO"
    target_role = Column(String, nullable=False)  # "BATTER", "PITCHER"
    effects = Column(JSON, nullable=False)
    description = Column(String, nullable=True)