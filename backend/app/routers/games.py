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

    En modo PVE el equipo visitante es la CPU.
    
    ⭐ NUEVO: El usuario puede elegir ser LOCAL (HOME) o VISITANTE (AWAY).
    Si elige AWAY, se intercambian automáticamente las posiciones.
    """
    
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
        user_lineup = db.query(UserLineup).filter(
            UserLineup.user_id == human_user_id,
            UserLineup.is_active == True
        ).first()
        if user_lineup and user_lineup.slots:
            lineup_cards = [
                card["id"] for slot, card in user_lineup.slots.items() 
                if slot != "P" and isinstance(card, dict) and "id" in card
            ][:9]
            pitcher_card = None
            if "P" in user_lineup.slots and isinstance(user_lineup.slots["P"], dict):
                pitcher_card = user_lineup.slots["P"]["id"]
            
            if human_is_home:
                home_lineup_ids = lineup_cards
                home_pitcher_id = pitcher_card
            else:
                away_lineup_ids = lineup_cards
                away_pitcher_id = pitcher_card

    # 2. Obtener datos de CPU (equipo rival)
    cpu_cards = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == rival_team_id).all()
    
    # ⭐ Cargar nombre completo del equipo rival desde la tabla Team
    from app.models import Team
    rival_team_obj = db.query(Team).filter(Team.id == rival_team_id).first()
    rival_team_name = rival_team_obj.name if rival_team_obj else rival_team_id
    
    # ⭐ FALLBACK: Si no hay cartas del equipo rival, usar cartas de cualquier equipo
    if not cpu_cards:
        print(f"⚠️  No hay cartas para equipo {rival_team_id}, buscando cartas de cualquier equipo...")
        cpu_cards = db.query(PlayerCardModel).all()
    
    if not cpu_cards:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No hay cartas disponibles en la base de datos. Ejecuta el seed primero."
        )

    # ⭐ ARREGLADO: Incluir is_two_way para Ohtani y otros jugadores con dos roles
    pitchers = [c for c in cpu_cards if c.position in ["SP", "RP", "CP", "TWP"] or c.is_two_way]
    batters = [c for c in cpu_cards if c.position not in ["SP", "RP", "CP"] or c.is_two_way]

    print(f"🔍 DEBUG create_game_session:")
    print(f"   rival_team_id: {rival_team_id}")
    print(f"   rival_team_name: {rival_team_name}")
    print(f"   cpu_cards: {len(cpu_cards)}")
    print(f"   pitchers available: {len(pitchers)}")
    print(f"   🎯 PITCHER LIST FOR CPU:")
    for p in pitchers:
        print(f"      - {p.name} ({p.id}) | Team: {p.team.name if p.team else 'UNKNOWN'} | OVR: {p.overall} | Pos: {p.position}")
    print(f"   batters available: {len(batters)} → {[b.name for b in batters[:3]]}")
    print(f"   home_pitcher_id (before): {home_pitcher_id}")
    print(f"   away_pitcher_id (before): {away_pitcher_id}")

    # Asignar cartas CPU según su posición
    if human_is_home:
        # CPU es visitante (away)
        if not away_pitcher_id and pitchers:
            away_pitcher_id = pitchers[0].id
            print(f"   ✅ Assigned away pitcher: {pitchers[0].name}")
        if (not away_lineup_ids or len(away_lineup_ids) < 9) and batters:
            away_lineup_ids = [c.id for c in batters[:9]]
            while len(away_lineup_ids) < 9 and cpu_cards:
                away_lineup_ids.append(cpu_cards[0].id)
            print(f"   ✅ Assigned away lineup: {len(away_lineup_ids)} cards")
    else:
        # CPU es local (home)
        if not home_pitcher_id and pitchers:
            home_pitcher_id = pitchers[0].id
            print(f"   ✅ Assigned home pitcher: {pitchers[0].name}")
        if (not home_lineup_ids or len(home_lineup_ids) < 9) and batters:
            home_lineup_ids = [c.id for c in batters[:9]]
            while len(home_lineup_ids) < 9 and cpu_cards:
                home_lineup_ids.append(cpu_cards[0].id)
            print(f"   ✅ Assigned home lineup: {len(home_lineup_ids)} cards")

    # Validaciones de seguridad
    if not home_pitcher_id or not away_pitcher_id:
        print(f"❌ ERROR: home_pitcher_id={home_pitcher_id}, away_pitcher_id={away_pitcher_id}")
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
        state_data={
            **sanitized_state,
            "user_role": "HOME" if user_id == game.home_user_id else "AWAY",  # ⭐ NUEVO
        }
    )


@router.get("/{game_id}/box-score", summary="Obtener box score de la partida")
def get_box_score(game_id: str, db: Session = Depends(get_db)):
    """
    Obtiene el resumen de estadísticas (box score) de una partida completada.
    
    Incluye:
    - Estadísticas de bateadores (AB, H, 2B, 3B, HR, RBI, R, SO, BB)
    - Estadísticas de pitchers (SO, BB, H, HR, R)
    """
    from app.engine.stats_recorder import get_game_box_score
    
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partida '{game_id}' no encontrada."
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
def get_player_game_stats(game_id: str, player_id: str, db: Session = Depends(get_db)):
    """
    Obtiene las estadísticas de un jugador específico en una partida.
    Puede ser bateador o pitcher.
    """
    from app.engine.stats_recorder import get_player_game_stats as calc_player_stats
    
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Partida '{game_id}' no encontrada."
        )
    
    stats = calc_player_stats(db, game_id, player_id)
    return {
        "game_id": game_id,
        "player_id": player_id,
        "stats": stats,
    }
