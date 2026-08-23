"""
Router: Gestión de Sesión de Juego 1v1
========================================
Endpoints para crear y consultar sesiones de juego:
  - POST /create        → Crea una nueva sesión e inicializa todo el estado del partido.
  - GET  /{game_id}     → Retorna el estado sanitizado (Fog of War aplicado según el rol del usuario).
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GameSession, PlayerCardModel
from app.schemas import CreateGameRequest, GameSessionResponse

from app.engine.deck_manager import initialize_tactics_state
from app.engine.fog_of_war import sanitize_state_for_player

router = APIRouter(prefix="/api/v1/games", tags=["Gestión de Sesión 1v1"])

@router.post("/create", response_model=GameSessionResponse, status_code=status.HTTP_201_CREATED, summary="Iniciar nueva partida 1v1")
def create_game_session(payload: CreateGameRequest, db: Session = Depends(get_db)):
    """
    Crea una nueva sesión de juego 1v1 e inicializa:
    - Marcador 0-0, Inning 1 Alta.
    - Lineups de 9 bateadores por equipo.
    - Mazos tácticos mezclados con mano inicial de 3 cartas.
    - Pitcher activo inicial (el visitante lanza en la Alta del primer inning).

    En modo PVE el equipo visitante es siempre CPU_BOT.
    """
    away_id = payload.away_user_id if payload.game_mode == "PVP" else "CPU_BOT"

    # Validar que existan los pitchers seleccionados usando el modelo correcto
    home_pitcher = db.query(PlayerCardModel).filter(PlayerCardModel.id == payload.home_pitcher_id).first()
    away_pitcher = db.query(PlayerCardModel).filter(PlayerCardModel.id == payload.away_pitcher_id).first()

    if not home_pitcher or not away_pitcher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uno o ambos lanzadores seleccionados no existen en el catálogo."
        )

    tactics_state = initialize_tactics_state(
        payload.home_tactics_deck,
        payload.away_tactics_deck
    )

    game = GameSession(
        id=f"game_{uuid.uuid4().hex[:8]}",
        home_user_id=payload.home_user_id,
        away_user_id=away_id,
        state_data={
            "mode": payload.game_mode,
            "difficulty": payload.difficulty,
            "home_lineup": payload.home_lineup,
            "away_lineup": payload.away_lineup,
            "home_batter_index": 0,
            "away_batter_index": 0,
            "tactics": tactics_state,
            "active_pitcher": payload.away_pitcher_id,  # El visitante lanza primero
            "active_batter": payload.home_lineup[0],    # El local batea primero (Baja)
            "runners": {"1b": None, "2b": None, "3b": None},
            "current_pitch": None,
            "active_tactics": {"home": None, "away": None},
            "pitch_counts": {},
            "last_event": "Juego iniciado",
            "is_game_over": False,
        }
    )

    db.add(game)
    db.commit()
    db.refresh(game)

    return game

@router.get("/{game_id}", response_model=GameSessionResponse, summary="Obtener estado sanitizado de la partida")
def get_game_session(
    game_id: str, 
    user_id: str = Query(..., description="ID del usuario que realiza la consulta"),
    db: Session = Depends(get_db)
):
    """
    Obtiene el estado de la partida aplicando Niebla de Guerra. 
    Si el bateador consulta, no verá la zona ni el tipo de pitcheo del rival.
    """
    
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la sesión de juego '{game_id}'."
        )

    # Sanitizar el estado filtrando datos ocultos
    sanitized_state = sanitize_state_for_player(
        state_data=game.state_data,
        requesting_user_id=user_id,
        home_user_id=game.home_user_id,
        away_user_id=game.away_user_id,
        is_top_inning=game.is_top_inning
    )

    # Retornar una copia con el estado filtrado
    return GameSessionResponse(
        id=game.id,
        home_user_id=game.home_user_id,
        away_user_id=game.away_user_id,
        current_inning=game.current_inning,
        is_top_inning=game.is_top_inning,
        outs=game.outs,
        balls=game.balls,
        strikes=game.strikes,
        score_home=game.score_home,
        score_away=game.score_away,
        state_data=sanitized_state
    )