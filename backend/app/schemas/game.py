from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# Crear sesión de juego
class CreateGameRequest(BaseModel):
    home_user_id: str
    away_user_id: Optional[str] = "CPU_BOT"
    game_mode: str = Field("PVP", description="'PVP' o 'PVE'")
    difficulty: Optional[str] = Field("MEDIUM", description="'EASY', 'MEDIUM' o 'HARD'")
    total_innings: Optional[int] = Field(9, description="Duración del partido: 3, 6 o 9 entradas")
    player_position: str = Field("HOME", description="'HOME' o 'AWAY' - posición elegida por el jugador humano")
    home_pitcher_id: Optional[str] = None
    away_pitcher_id: Optional[str] = None
    home_lineup: Optional[List[str]] = Field(default_factory=list)
    away_lineup: Optional[List[str]] = Field(default_factory=list)
    home_tactics_deck: Optional[List[str]] = Field(default_factory=list)
    away_tactics_deck: Optional[List[str]] = Field(default_factory=list)

# Respuesta del estado de la partida
class GameSessionResponse(BaseModel):
    id: str
    home_user_id: str
    away_user_id: str
    current_inning: int
    is_top_inning: bool
    outs: int
    balls: int
    strikes: int
    score_home: int
    score_away: int
    state_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True



# --- Módulo 3: Gameplay ---

class PlayTacticRequest(BaseModel):
    player_role: str = Field(..., description="'PITCHER' o 'BATTER'")
    tactic_id: str


class PitchActionRequest(BaseModel):
    pitch_type: str = Field(..., description="Ej. 'FF', 'SL', 'CH', 'CU'")
    zone: int = Field(..., ge=1, le=9, description="Cuadrante de la strike zone (1 al 9)")


class SwingActionRequest(BaseModel):
    swing_type: str = Field(..., description="'NORMAL', 'POWER', 'TAKE' o 'BUNT'")
    guessed_zone: Optional[int] = Field(None, ge=1, le=9)
    guessed_pitch: Optional[str] = None


class PlayResultResponse(BaseModel):
    event: str
    description: str
    outs: int
    balls: int
    strikes: int
    score_home: int
    score_away: int
    current_inning: int
    is_top_inning: bool
    state_data: Optional[Dict[str, Any]] = None


class ChangePitcherRequest(BaseModel):
    new_pitcher_id: str = Field(..., description="ID de la carta del lanzador de relevo")
    player_role: str = Field(default="PITCHER", description="Siempre 'PITCHER' — campo legado opcional")


# Nuevo esquema para robo de base
class StealBaseRequest(BaseModel):
    target_base: str = Field(..., description="'2b' o '3b'")
