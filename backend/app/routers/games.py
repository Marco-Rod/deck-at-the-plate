"""
Router: Gestión de Sesión de Juego 1v1
========================================
Endpoints para crear y consultar sesiones de juego:
  - POST /create        → Crea una nueva sesión e inicializa todo el estado del partido.
  - GET  /{game_id}     → Retorna el estado sanitizado (Fog of War aplicado según el rol del usuario).
"""
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GameSession
from app.schemas import CreateGameRequest, GameSessionResponse
from app.auth import get_current_user

from app.engine.deck_manager import initialize_tactics_state
from app.engine.fog_of_war import sanitize_state_for_player
from app.repositories import (
    find_all_cards,
    find_cards_by_team,
    get_active_lineup,
    get_card_by_id,
    get_game_by_id,
    get_team_by_id,
)

router = APIRouter(prefix="/api/v1/games", tags=["Gestión de Sesión 1v1"])

logger = logging.getLogger(__name__)

# Mazos de tácticas predeterminados por defecto
DEFAULT_TACTICS_DECK = ["t1", "t2", "t3", "t4", "t1"]

@router.post("/create", response_model=GameSessionResponse, status_code=status.HTTP_201_CREATED, summary="Iniciar nueva partida 1v1")
def create_game_session(
    payload: CreateGameRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Crea una nueva sesión de juego 1v1 e inicializa:
    - Marcador 0-0, Inning 1 Alta.
    - Lineups de 9 bateadores por equipo.
    - Mazos tácticos mezclados con mano inicial de 3 cartas.
    - Pitcher activo inicial (el visitante lanza en la Alta del primer inning).

    En modo PVE el equipo visitante es la CPU.

    Seguridad: el usuario humano de la partida se deriva del JWT; no se permite
    crear una partida en nombre de otro usuario.
    """

    # El jugador humano siempre debe ser el usuario autenticado.
    if payload.home_user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes crear una partida en nombre de otro usuario.",
        )

    # ⭐ MAPEO: Determinar posiciones basadas en player_position
    if payload.player_position == "AWAY":
        # Usuario elige ser visitante → CPU es local
        home_user_id = "CPU_BOT"
        away_user_id = payload.home_user_id
        rival_team_id = payload.away_user_id  # Equipo CPU
    elif payload.player_position == "HOME":
        # Usuario elige ser local (comportamiento actual)
        home_user_id = payload.home_user_id
        away_user_id = "CPU_BOT"
        rival_team_id = payload.away_user_id  # Equipo CPU
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="player_position debe ser 'HOME' o 'AWAY'"
        )

    # 1. Obtener lineup del jugador humano
    human_user_id = payload.home_user_id  # El usuario humano siempre viene en home_user_id
    human_is_home = (payload.player_position == "HOME")
    
    # Inicializar variables
    home_lineup_ids = []
    away_lineup_ids = []
    home_pitcher_id = None
    away_pitcher_id = None
    
    # Determinar lineup y pitcher del usuario humano según su posición
    if human_is_home:
        home_lineup_ids = payload.home_lineup or []
        home_pitcher_id = payload.home_pitcher_id
    else:
        away_lineup_ids = payload.away_lineup or []
        away_pitcher_id = payload.away_pitcher_id

    # Si no viene provisto, buscar del usuario
    if (human_is_home and (not home_lineup_ids or len(home_lineup_ids) < 9)) or \
       (not human_is_home and (not away_lineup_ids or len(away_lineup_ids) < 9)):
        user_lineup = get_active_lineup(db, human_user_id)
        if user_lineup and user_lineup.slots:
            # Normalizar slots: se acepta tanto el objeto completo de la carta
            # ({"id": "card_xxx", ...}) como un id plano ("card_xxx"). Esto hace
            # la carga robusta ante cualquier formato previamente persistido.
            lineup_cards = []
            pitcher_card = None
            for slot, card in user_lineup.slots.items():
                card_id = (
                    card.get("id")
                    if isinstance(card, dict) and isinstance(card.get("id"), str)
                    else card if isinstance(card, str) else None
                )
                if not card_id:
                    continue
                if slot == "P":
                    pitcher_card = card_id
                else:
                    lineup_cards.append(card_id)
            lineup_cards = lineup_cards[:9]
            
            if human_is_home:
                home_lineup_ids = lineup_cards
                home_pitcher_id = pitcher_card
            else:
                away_lineup_ids = lineup_cards
                away_pitcher_id = pitcher_card

    # 2. Obtener datos de CPU (equipo rival)
    cpu_cards = find_cards_by_team(db, rival_team_id)
    
    # ⭐ Cargar nombre completo del equipo rival desde la tabla Team
    rival_team_obj = get_team_by_id(db, rival_team_id)
    rival_team_name = rival_team_obj.name if rival_team_obj else rival_team_id
    
    # ⭐ FALLBACK: Si no hay cartas del equipo rival, usar cartas de cualquier equipo
    if not cpu_cards:
        logger.warning("No hay cartas para equipo %s; usando cartas de cualquier equipo.", rival_team_id)
        cpu_cards = find_all_cards(db)
    
    if not cpu_cards:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No hay cartas disponibles en la base de datos. Ejecuta el seed primero."
        )

    # ⭐ ARREGLADO: Incluir is_two_way para Ohtani y otros jugadores con dos roles
    pitchers = [c for c in cpu_cards if c.position in ["SP", "RP", "CP", "TWP"] or c.is_two_way]
    batters = [c for c in cpu_cards if c.position not in ["SP", "RP", "CP"] or c.is_two_way]

    # Asignar cartas CPU según su posición
    if human_is_home:
        # CPU es visitante (away)
        if not away_pitcher_id and pitchers:
            away_pitcher_id = pitchers[0].id
        if (not away_lineup_ids or len(away_lineup_ids) < 9) and batters:
            away_lineup_ids = [c.id for c in batters[:9]]
            while len(away_lineup_ids) < 9 and cpu_cards:
                away_lineup_ids.append(cpu_cards[0].id)
    else:
        # CPU es local (home)
        if not home_pitcher_id and pitchers:
            home_pitcher_id = pitchers[0].id
        if (not home_lineup_ids or len(home_lineup_ids) < 9) and batters:
            home_lineup_ids = [c.id for c in batters[:9]]
            while len(home_lineup_ids) < 9 and cpu_cards:
                home_lineup_ids.append(cpu_cards[0].id)

    # Validaciones de seguridad
    if not home_pitcher_id or not away_pitcher_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Se requiere un lanzador válido para ambos equipos. home={home_pitcher_id}, away={away_pitcher_id}"
        )

    home_tactics = payload.home_tactics_deck or DEFAULT_TACTICS_DECK
    away_tactics = payload.away_tactics_deck or DEFAULT_TACTICS_DECK

    tactics_state = initialize_tactics_state(home_tactics, away_tactics)

    total_innings = payload.total_innings if payload.total_innings in (3, 6, 9) else 9

    game = GameSession(
        id=f"game_{uuid.uuid4().hex[:8]}",
        home_user_id=home_user_id,
        away_user_id=away_user_id,
        state_data={
            "mode": payload.game_mode,
            "difficulty": payload.difficulty,
            "total_innings": total_innings,
            "home_lineup": home_lineup_ids,
            "away_lineup": away_lineup_ids,
            "home_batter_index": 0,
            "away_batter_index": 0,
            "tactics": tactics_state,
            "active_pitcher": home_pitcher_id,  # El local (home) lanza en la Alta
            "active_batter": away_lineup_ids[0] if away_lineup_ids else None,
            "home_pitcher_id": home_pitcher_id,
            "away_pitcher_id": away_pitcher_id,
            "runners": {"1b": None, "2b": None, "3b": None},
            "current_pitch": None,
            "active_tactics": {"home": None, "away": None},
            "pitch_counts": {},
            "last_event": "Juego iniciado",
            "is_game_over": False,
            "rival_team_name": rival_team_name,  # ⭐ NUEVO: nombre del equipo rival
            "user_role": payload.player_position,  # ⭐ NUEVO: posición del usuario (HOME o AWAY)
        }
    )

    db.add(game)
    db.commit()
    db.refresh(game)

    logger.info(
        "Partida creada: %s | modo=%s | dificultad=%s | local=%s | visitante=%s",
        game.id, payload.game_mode, payload.difficulty, home_user_id, away_user_id,
    )

    return game

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
    from app.engine.stats_recorder import get_game_box_score
    
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
    from app.engine.stats_recorder import get_player_game_stats as calc_player_stats
    
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
