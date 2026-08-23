from pydantic import BaseModel, ConfigDict
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