from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from app.models.card import CardRarity


class TeamBaseSchema(BaseModel):
    id: str
    name: str
    city: str
    primary_color: str
    secondary_color: str

    model_config = ConfigDict(from_attributes=True)


class PlayerCardSchema(BaseModel):
    id: str
    team_id: Optional[str] = None
    name: str
    number: str
    position: str
    overall: int
    rarity: CardRarity
    is_two_way: bool
    power: int
    contact: int
    velocity: int
    control: int

    model_config = ConfigDict(from_attributes=True)


class TeamRosterResponseSchema(BaseModel):
    team: TeamBaseSchema
    total_players: int
    roster: List[PlayerCardSchema]