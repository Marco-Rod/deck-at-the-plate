import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
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