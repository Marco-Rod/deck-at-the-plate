from pydantic import BaseModel, ConfigDict, Field
from typing import List
from datetime import datetime
from app.schemas.cards import PlayerCardSchema


class WalletSchema(BaseModel):
    stamps: int
    gems: int

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponseSchema(BaseModel):
    user_id: str
    username: str
    created_at: datetime
    wallet: WalletSchema


class InventoryItemSchema(BaseModel):
    inventory_id: str
    acquired_at: datetime
    card: PlayerCardSchema


class UserInventoryResponseSchema(BaseModel):
    user_id: str
    total_cards: int
    inventory: List[InventoryItemSchema]


# --- Autenticación ---

class RegisterRequest(BaseModel):
    """Payload para registrar un nuevo usuario."""
    username: str = Field(..., min_length=3, max_length=30, description="Nombre de usuario único (3–30 caracteres)")
    password: str = Field(..., min_length=6, description="Contraseña (mínimo 6 caracteres)")
    has_completed_onboarding: bool = False

class LoginResponse(BaseModel):
    """Respuesta del endpoint de login con el JWT y datos básicos del usuario."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str