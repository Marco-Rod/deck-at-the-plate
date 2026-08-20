import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GameSession, PlayerCard
from app.schemas import CreateGameRequest, GameSessionResponse

from app.engine.deck_manager import initialize_tactics_state
from app.engine.fog_of_war import sanitize_state_for_player

router = APIRouter(prefix="/api/v1/games", tags=["Gestión de Sesión 1v1"])

@router.post("/create", response_model=GameSessionResponse, status_code=status.HTTP_201_CREATED, summary="Iniciar nueva partida 1v1")
def create_game_session(payload: CreateGameRequest, db: Session = Depends(get_db)):
    """
    Crea una nueva partida 1v1 e inicializa el marcador (0-0), Inning 1 Alta y el estado de la mesa.
    """
    # Validar que existan los pitchers seleccionados
    home_pitcher = db.query(PlayerCard).filter(PlayerCard.id == payload.home_pitcher_id).first()
    away_pitcher = db.query(PlayerCard).filter(PlayerCard.id == payload.away_pitcher_id).first()

    if not home_pitcher or not away_pitcher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uno o ambos lanzadores seleccionados no existen en el catálogo."
        )
    
    tactics_state = initialize_tactics_state(
        payload.home_tactics_deck, 
        payload.away_tactics_deck
    )

    # Estado inicial de la partida
    initial_state = {
        "home_lineup": payload.home_lineup,
        "away_lineup": payload.away_lineup,
        "home_batter_index": 0,
        "away_batter_index": 0,
        "tactics": tactics_state,  # Contiene deck, hand y discard de home/away
        "active_pitcher": payload.away_pitcher_id,
        "active_batter": payload.home_lineup[0],
        "runners": {"1b": None, "2b": None, "3b": None},
        "current_pitch": None,
        "active_tactics": {"home": None, "away": None},
        "last_event": "Juego iniciado"
    }

    game_id = f"game_{uuid.uuid4().hex[:10]}"

    new_game = GameSession(
        id=game_id,
        home_user_id=payload.home_user_id,
        away_user_id=payload.away_user_id,
        current_inning=1,
        is_top_inning=True,
        outs=0,
        balls=0,
        strikes=0,
        score_home=0,
        score_away=0,
        state_data=initial_state
    )

    db.add(new_game)
    db.commit()
    db.refresh(new_game)

    return new_game

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