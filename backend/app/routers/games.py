"""
Router: Gestión de Sesión de Juego 1v1
========================================
Endpoints para crear y consultar sesiones de juego:
  - POST /create        → Crea una nueva sesión e inicializa todo el estado del partido.
  - GET  /{game_id}     → Retorna el estado sanitizado (Fog of War aplicado según el rol del usuario).
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CreateGameRequest, GameSessionResponse
from app.auth import get_current_user

from app.engine.fog_of_war import sanitize_state_for_player
from app.repositories import (
    get_card_by_id,
    get_game_by_id,
)
from app.services.game_session_service import GameSessionService

router = APIRouter(prefix="/api/v1/games", tags=["Gestión de Sesión 1v1"])

logger = logging.getLogger(__name__)

@router.post("/create", response_model=GameSessionResponse, status_code=status.HTTP_201_CREATED, summary="Iniciar nueva partida 1v1")
def create_game_session(
    payload: CreateGameRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Crea una nueva sesión de juego 1v1 e inicializa todo el estado del partido.

    Seguridad: el usuario humano de la partida se deriva del JWT; no se permite
    crear una partida en nombre de otro usuario. La inicialización de la sesión
    (lineups, roster CPU, tácticas, state_data) queda en GameSessionService.
    """
    # El jugador humano siempre debe ser el usuario autenticado.
    if payload.home_user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes crear una partida en nombre de otro usuario.",
        )

    return GameSessionService.create(db, payload)

@router.get("/{game_id}", response_model=GameSessionResponse, summary="Obtener estado sanitizado de la partida")
def get_game_session(
    game_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Obtiene el estado de la partida aplicando Niebla de Guerra.
    Si el bateador consulta, no verá la zona ni el tipo de pitcheo del rival.

    Seguridad: la identidad del usuario se deriva del JWT (no del query param),
    y solo un usuario perteneciente a la partida puede consultarla.
    """
    game = get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la sesión de juego '{game_id}'."
        )

    # Solo los usuarios involucrados en la partida pueden acceder a su estado.
    if current_user_id not in (game.home_user_id, game.away_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta partida."
        )

    state = dict(game.state_data or {})
    active_pitcher_id = state.get("active_pitcher")
    active_pitcher = get_card_by_id(db, active_pitcher_id)

    sanitized_state = sanitize_state_for_player(
        state_data=game.state_data,
        requesting_user_id=current_user_id,
        home_user_id=game.home_user_id,
        away_user_id=game.away_user_id,
        is_top_inning=game.is_top_inning
    )

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
        state_data={
            **sanitized_state,
            "user_role": "HOME" if current_user_id == game.home_user_id else "AWAY",
        }
    )


@router.get("/{game_id}/box-score", summary="Obtener box score de la partida")
def get_box_score(
    game_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Obtiene el resumen de estadísticas (box score) de una partida completada.
    
    Incluye:
    - Estadísticas de bateadores (AB, H, 2B, 3B, HR, RBI, R, SO, BB)
    - Estadísticas de pitchers (SO, BB, H, HR, R)

    Seguridad: solo los usuarios participantes de la partida pueden consultarla.
    """
    from app.repositories import get_game_box_score
    
    game = get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partida '{game_id}' no encontrada."
        )

    # Solo los usuarios involucrados en la partida pueden acceder.
    if current_user_id not in (game.home_user_id, game.away_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta partida."
        )
    
    box_score = get_game_box_score(db, game_id)
    return {
        "game_id": game_id,
        "final_score": {
            "home": game.score_home,
            "away": game.score_away,
        },
        "box_score": box_score,
    }


@router.get("/{game_id}/player/{player_id}/stats", summary="Obtener estadísticas de un jugador en la partida")
def get_player_game_stats(
    game_id: str,
    player_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Obtiene las estadísticas de un jugador específico en una partida.
    Puede ser bateador o pitcher.

    Seguridad: solo los usuarios participantes de la partida pueden consultarla.
    """
    from app.repositories import get_player_game_stats as calc_player_stats
    
    game = get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partida '{game_id}' no encontrada."
        )

    # Solo los usuarios involucrados en la partida pueden acceder.
    if current_user_id not in (game.home_user_id, game.away_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta partida."
        )
    
    stats = calc_player_stats(db, game_id, player_id)
    return {
        "game_id": game_id,
        "player_id": player_id,
        "stats": stats,
    }
