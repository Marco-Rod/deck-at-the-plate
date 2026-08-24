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
from app.models import GameSession, PlayerCardModel, UserLineup
from app.schemas import CreateGameRequest, GameSessionResponse

from app.engine.deck_manager import initialize_tactics_state
from app.engine.fog_of_war import sanitize_state_for_player

router = APIRouter(prefix="/api/v1/games", tags=["Gestión de Sesión 1v1"])

# Mazos de tácticas predeterminados por defecto
DEFAULT_TACTICS_DECK = ["t1", "t2", "t3", "t4", "t1"]

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

    # 1. Obtener lineup del jugador local si no viene provisto
    home_lineup_ids = payload.home_lineup
    home_pitcher_id = payload.home_pitcher_id

    if not home_lineup_ids or len(home_lineup_ids) < 9:
        user_lineup = db.query(UserLineup).filter(
            UserLineup.user_id == payload.home_user_id,
            UserLineup.is_active == True
        ).first()
        if user_lineup and user_lineup.slots:
            home_lineup_ids = [
                card["id"] for slot, card in user_lineup.slots.items() 
                if slot != "P" and isinstance(card, dict) and "id" in card
            ][:9]
            if "P" in user_lineup.slots and isinstance(user_lineup.slots["P"], dict):
                home_pitcher_id = user_lineup.slots["P"]["id"]

    # 2. Si es PvE y faltan datos de la CPU, rellenar automáticamente con el equipo CPU rival
    away_lineup_ids = payload.away_lineup
    away_pitcher_id = payload.away_pitcher_id

    if payload.game_mode == "PVE":
        # Buscar cartas asociadas al equipo CPU rival
        cpu_team_id = payload.away_user_id if payload.away_user_id != "CPU_BOT" else "JAL"
        cpu_cards = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == cpu_team_id).all()
        
        if not cpu_cards:
            cpu_cards = db.query(PlayerCardModel).all()

        pitchers = [c for c in cpu_cards if c.position in ["SP", "RP", "CP"]]
        batters = [c for c in cpu_cards if c.position not in ["SP", "RP", "CP"]]

        if not away_pitcher_id and pitchers:
            away_pitcher_id = pitchers[0].id
        if (not away_lineup_ids or len(away_lineup_ids) < 9) and batters:
            away_lineup_ids = [c.id for c in batters[:9]]
            while len(away_lineup_ids) < 9 and cpu_cards:
                away_lineup_ids.append(cpu_cards[0].id)

    # Validaciones de seguridad
    if not home_pitcher_id or not away_pitcher_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere un lanzador válido para ambos equipos."
        )

    home_tactics = payload.home_tactics_deck or DEFAULT_TACTICS_DECK
    away_tactics = payload.away_tactics_deck or DEFAULT_TACTICS_DECK

    tactics_state = initialize_tactics_state(home_tactics, away_tactics)

    game = GameSession(
        id=f"game_{uuid.uuid4().hex[:8]}",
        home_user_id=payload.home_user_id,
        away_user_id=away_id,
        state_data={
            "mode": payload.game_mode,
            "difficulty": payload.difficulty,
            "home_lineup": home_lineup_ids,
            "away_lineup": away_lineup_ids,
            "home_batter_index": 0,
            "away_batter_index": 0,
            "tactics": tactics_state,
            "active_pitcher": away_pitcher_id,  # El visitante lanza primero en la Alta
            "active_batter": home_lineup_ids[0] if home_lineup_ids else None,
            "runners": {"1b": None, "2b": None, "3b": None},
            "current_pitch": None,
            "active_tactics": {"home": None, "away": None},
            "pitch_counts": {},
            "last_event": "Juego iniciado vs CPU",
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

    sanitized_state = sanitize_state_for_player(
        state_data=game.state_data,
        requesting_user_id=user_id,
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
        state_data=sanitized_state
    )