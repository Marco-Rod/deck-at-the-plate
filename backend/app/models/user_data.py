import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relaciones 1:1 con Cartera y 1:N con Inventario
    wallet = relationship("UserWallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    inventory = relationship("UserCardInventory", back_populates="user", cascade="all, delete-orphan")
    favorite_team_id = Column(String(3), ForeignKey("teams.id"), nullable=True)
    has_completed_onboarding = Column(Boolean, default=False)
    lineups = relationship("UserLineup", back_populates="user", cascade="all, delete-orphan")
    team = relationship("UserTeam", back_populates="user", uselist=False)

class UserWallet(Base):
    __tablename__ = "user_wallets"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    stamps = Column(Integer, default=1000)  # Moneda principal para sobres
    gems = Column(Integer, default=0)       # Moneda premium

    user = relationship("User", back_populates="wallet")


class UserCardInventory(Base):
    __tablename__ = "user_card_inventories"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    card_id = Column(String, ForeignKey("player_cards.id"), index=True, nullable=False)
    acquired_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="inventory")
    card = relationship("PlayerCardModel", back_populates="inventories")


class UserLineup(Base):
    __tablename__ = "user_lineups"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, default="Lineup Principal")
    is_active = Column(Boolean, default=True)
    
    # Guarda el mapa completo: {"P": card_obj, "C": card_obj, "1B": card_obj, ...}
    slots = Column(JSON, nullable=False, default={})
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación bidireccional con el usuario
    user = relationship("User", back_populates="lineups")


class UserTeam(Base):
    __tablename__ = "user_teams"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Identidad del Club Personalizado
    name = Column(String(50), nullable=False)        # Ej. "Tigres"
    short_name = Column(String(3), nullable=False)   # Ej. "TIG"
    city = Column(String(50), default="Jalisco")     # Ej. "Zapopan"
    stadium_name = Column(String(50), default="Estadio Municipal")
    
    # Personalización Estética
    primary_color = Column(String(7), default="#C5A059")   # Hex
    secondary_color = Column(String(7), default="#1A3323") # Hex
    logo_id = Column(String(50), default="logo_baseball_01")
    
    # Franquicia MLB seleccionada para el sobre base (Dodgers, Yankees, etc.)
    base_franchise = Column(String(10), nullable=False, default="LAD")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relación
    user = relationship("User", back_populates="team")