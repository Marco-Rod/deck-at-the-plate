from pydantic import BaseModel
from typing import List
from app.schemas.cards import PlayerCardSchema


class StarterPackResponseSchema(BaseModel):
    message: str
    user_id: str
    cards_claimed: int
    cards: List[PlayerCardSchema]


class OpenPackResponseSchema(BaseModel):
    message: str
    user_id: str
    cards_drawn: int
    cards: List[PlayerCardSchema]