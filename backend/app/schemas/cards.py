from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from app.models.card import CardRarity


class TeamBaseSchema(BaseModel):
    id: str
    name: str
    city: str
    primary_color: str
    secondary_color: str

    model_config = ConfigDict(from_attributes=True)


class PitchAttributeSchema(BaseModel):
    pitch_type: str = Field(..., example="4-SEAM")
    velocity: int = Field(..., ge=50, le=102)
    control: int = Field(..., ge=1, le=99)
    movement: int = Field(..., ge=1, le=99)

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
    
    # Atributos de Bateo
    power: int
    contact: int
    
    # Atributos de Pitcheo
    velocity: int
    control: int
    movement: int = 50
    
    # Repertorio de lanzamientos (opcional para bateadores puros)
    repertoire: Optional[List[PitchAttributeSchema]] = []

    model_config = ConfigDict(from_attributes=True)


class TeamRosterResponseSchema(BaseModel):
    team: TeamBaseSchema
    total_players: int
    roster: List[PlayerCardSchema]