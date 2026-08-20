from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.auth import get_current_user
from app.database import get_db
from app.models import GameSession, PlayerCard, TacticCard
from app.schemas import (
    PlayTacticRequest,
    PitchActionRequest,
    SwingActionRequest,
    PlayResultResponse
)
from app.engine.calculator import calculate_play_outcome
from app.engine.state_manager import process_at_bat_transition
from app.engine.fatigue_manager import apply_pitcher_fatigue
from app.engine.tactical_actions import resolve_bunt, resolve_steal
from app.engine.websocket_manager import manager
from app.engine.turn_guard import verify_player_turn

from app.schemas import ChangePitcherRequest
from app.schemas import StealBaseRequest

router = APIRouter(prefix="/api/v1/games", tags=["Motor de Jugabilidad 1v1"])


@router.post("/{game_id}/play-tactic", summary="Activar carta táctica")
def play_tactic(game_id: str, payload: PlayTacticRequest, db: Session = Depends(get_db)):
    """
    Registra el uso de una carta táctica para el turno actual en state_data.
    Valida que las cartas de categoría EXTRA_INNINGS solo se activen a partir del inning 10.
    """
    player_key = "home" if payload.player_role.upper() == "BATTER" and game.is_top_inning else "away"
    
    # Ajustar según corresponda al rol/equipo
    tactics_data = state.get("tactics", {}).get(player_key, {})
    player_hand = tactics_data.get("hand", [])
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    tactic = db.query(TacticCard).filter(TacticCard.id == payload.tactic_id).first()
    
    # Mover la carta usada de la mano al descarte
    discard_used_tactic(state["tactics"], player_key, payload.tactic_id)
    
    if payload.tactic_id not in player_hand:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La carta seleccionada no se encuentra en la mano actual del jugador."
        )
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Sesión de juego no encontrada."
        )
    
    if not tactic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Carta táctica no encontrada."
        )

    # Restricción de Inning para cartas de Muerte Súbita / Extra Innings
    if tactic.category == "EXTRA_INNINGS" and game.current_inning < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La carta táctica '{tactic.name}' solo se puede activar en extra innings (Entrada 10+)."
        )

    state = dict(game.state_data or {})
    active_tactics = state.get("active_tactics", {"home": None, "away": None})

    role_key = "pitcher" if payload.player_role.upper() == "PITCHER" else "batter"
    active_tactics[role_key] = tactic.id
    state["active_tactics"] = active_tactics

    game.state_data = state
    db.commit()

    return {
        "status": "ok", 
        "message": f"Táctica '{tactic.name}' activada para este enfrentamiento."
    }


@router.post("/{game_id}/pitch", summary="Registrar picheo (Fase 1)")
async def select_pitch(
    game_id: str, 
    payload: PitchActionRequest, 
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    Guarda la selección secreta del lanzador (tipo de tiro y zona 1-9) esperando el swing.
    """
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    # Validar que sea el turno del lanzador autenticado
    verify_player_turn(game, current_user_id, required_role="PITCHER")

    state = dict(game.state_data or {})
    state["current_pitch"] = {
        "pitch_type": payload.pitch_type,
        "zone": payload.zone
    }

    game.state_data = state
    db.commit()
    
    # Emite evento en tiempo real a ambos clientes conectados
    await manager.broadcast_to_game(game_id, {
        "type": "PITCH_COMMITTED",
        "message": "El lanzador ha ejecutado su picheo. Esperando swing del bateador.",
        "has_pitched": True
    })

    return {
        "status": "ok",
        "message": "Picheo registrado exitosamente. Notificación enviada."
    }


@router.post("/{game_id}/swing", response_model=PlayResultResponse, summary="Ejecutar swing y resolver jugada (Fase 2 y 3)")
async def execute_swing(
    game_id: str, 
    payload: SwingActionRequest, 
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    Procesa la acción del bateador, calcula la fatiga del picher, aplica los modificadores
    de cartas tácticas, ejecuta la matemática de Statcast y actualiza el estado completo del juego.
    """
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    # Validar que sea el turno del bateador autenticado
    verify_player_turn(game, current_user_id, required_role="BATTER")

    state = dict(game.state_data or {})
    current_pitch = state.get("current_pitch")

    if not current_pitch:
        raise HTTPException(
            status_code=400,
            detail="El lanzador aún no ha realizado su picheo para este turno."
        )

    # 1. Incrementar contador de lanzamientos y aplicar fatiga al picher activo
    pitch_counts = state.get("pitch_counts", {})
    active_pitcher_id = state.get("active_pitcher")

    current_count = pitch_counts.get(active_pitcher_id, 0) + 1
    pitch_counts[active_pitcher_id] = current_count
    state["pitch_counts"] = pitch_counts

    # 2. Obtener cartas activas desde la base de datos (Pitcher y Bateador activo)
    active_batter_id = state.get("active_batter", "card_nyy_soto_2025")

    pitcher_card = db.query(PlayerCard).filter(PlayerCard.id == active_pitcher_id).first() if active_pitcher_id else None
    batter_card = db.query(PlayerCard).filter(PlayerCard.id == active_batter_id).first() if active_batter_id else None

    raw_pitcher_attrs = pitcher_card.attributes if pitcher_card else {"velocidad": 90, "control": 80, "movimiento": 80}
    batter_attrs = batter_card.attributes if batter_card else {"contacto": 80, "poder": 80, "vision": 80}

    # Aplicar fatiga al picher basándonos en sus envíos totales
    pitcher_attrs = apply_pitcher_fatigue(raw_pitcher_attrs, current_count)

    # 3. Procesar modificadores de cartas tácticas activas
    active_tactics = state.get("active_tactics", {})
    tactics_modifiers = {"batter_con": 1.0, "batter_pwr": 1.0, "batter_vis": 1.0, "pitcher_mov": 1.0}

    if payload.swing_type == "BUNT":
        raw_event, description, sac_success = resolve_bunt(pitcher_attrs, batter_attrs, state.get("runners", {}))
        
        if sac_success and any(state.get("runners", {}).values()):
            # Si fue sacrificio exitoso, forzar avance de corredores
            runners = state.get("runners", {})
            new_runners = {"1b": None, "2b": None, "3b": None}
            if runners.get("2b"): new_runners["3b"] = runners["2b"]
            if runners.get("1b"): new_runners["2b"] = runners["1b"]
            state["runners"] = new_runners

    if active_tactics.get("batter"):
        tac = db.query(TacticCard).filter(TacticCard.id == active_tactics["batter"]).first()
        if tac:
            for eff in tac.effects:
                attr = eff.get("attribute")
                val = eff.get("value", 0) / 100.0
                if attr == "vision":
                    tactics_modifiers["batter_vis"] += val
                elif attr == "contacto":
                    tactics_modifiers["batter_con"] += val
                elif attr == "poder":
                    tactics_modifiers["batter_pwr"] += val

    if active_tactics.get("pitcher"):
        tac = db.query(TacticCard).filter(TacticCard.id == active_tactics["pitcher"]).first()
        if tac:
            for eff in tac.effects:
                attr = eff.get("attribute")
                val = eff.get("value", 0) / 100.0
                if attr == "movimiento":
                    tactics_modifiers["pitcher_mov"] += val

    # 4. Calcular resultado mediante el motor matemático (Statcast + RNG Ponderado)
    raw_event, description = calculate_play_outcome(
        pitcher_attrs=pitcher_attrs,
        batter_attrs=batter_attrs,
        pitch_selected=current_pitch,
        swing_selected={
            "swing_type": payload.swing_type,
            "guessed_zone": payload.guessed_zone,
            "guessed_pitch": payload.guessed_pitch
        },
        tactics_modifiers=tactics_modifiers
    )

    # 5. Transición de estado (conteo, corredores en base, rotación del lineup y cambio de entrada)
    at_bat_ended, inning_ended, event = process_at_bat_transition(game, raw_event, state)

    # Ajustar descripciones de cierre
    if event == "STRIKEOUT":
        description = "¡Tercer strike! Bateador ponchado."
    elif event == "WALK":
        description = "Cuatro bolas malas. Bateador toma base por bolas."

    if inning_ended:
        description += " Tres outs registrados. Cambio de entrada."

    # 6. Limpiar picheo procesado y actualizar estado
    state["current_pitch"] = None
    state["last_event"] = event
    game.state_data = state

    db.commit()
    db.refresh(game)

    # Emite el resultado completo a todos los clientes en la sala
    await manager.broadcast_to_game(game_id, {
        "type": "PLAY_RESOLVED",
        "event": event,
        "description": description,
        "outs": game.outs,
        "balls": game.balls,
        "strikes": game.strikes,
        "score_home": game.score_home,
        "score_away": game.score_away,
        "current_inning": game.current_inning,
        "is_top_inning": game.is_top_inning,
        "state_data": game.state_data
    })

    return PlayResultResponse(
        event=event,
        description=description,
        outs=game.outs,
        balls=game.balls,
        strikes=game.strikes,
        score_home=game.score_home,
        score_away=game.score_away,
        current_inning=game.current_inning,
        is_top_inning=game.is_top_inning,
        state_data=game.state_data
    )

@router.post("/{game_id}/change-pitcher", summary="Realizar cambio de relevista (Bullpen)")
def change_pitcher(game_id: str, payload: ChangePitcherRequest, db: Session = Depends(get_db)):
    """
    Sustituye al abridor o relevista actual por una nueva carta de picher del bullpen.
    """
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    new_pitcher = db.query(PlayerCard).filter(PlayerCard.id == payload.new_pitcher_id).first()
    if not new_pitcher or new_pitcher.role != "Pitcher":
        raise HTTPException(status_code=400, detail="La carta indicada no es un lanzador válido.")

    state = dict(game.state_data or {})
    state["active_pitcher"] = payload.new_pitcher_id
    
    # Inicializar el contador de lanzamientos del nuevo relevista en 0
    pitch_counts = state.get("pitch_counts", {})
    pitch_counts[payload.new_pitcher_id] = 0
    state["pitch_counts"] = pitch_counts

    game.state_data = state
    db.commit()

    return {
        "status": "ok",
        "message": f"Cambio de picher completado. Entra a la loma: {new_pitcher.name}.",
        "active_pitcher": payload.new_pitcher_id
    }

@router.post("/{game_id}/steal", summary="Intentar robo de base")
async def steal_base(game_id: str, payload: StealBaseRequest, db: Session = Depends(get_db)):
    """
    Ejecuta un intento de robo de base (2B o 3B) por parte del equipo a la ofensiva.
    """
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    state = dict(game.state_data or {})
    active_pitcher_id = state.get("active_pitcher")
    pitcher_card = db.query(PlayerCard).filter(PlayerCard.id == active_pitcher_id).first() if active_pitcher_id else None
    pitcher_attrs = pitcher_card.attributes if pitcher_card else {"velocidad": 90, "control": 80}

    runners = state.get("runners", {"1b": None, "2b": None, "3b": None})
    success, description = resolve_steal(pitcher_attrs, runners, payload.target_base)

    from_base = "1b" if payload.target_base == "2b" else "2b"

    if success:
        # Mover corredor a la base robada
        runners[payload.target_base] = runners[from_base]
        runners[from_base] = None
    else:
        # Out atrapado robando (Caught Stealing)
        runners[from_base] = None
        game.outs += 1

        if game.outs >= 3:
            game.outs = 0
            game.balls = 0
            game.strikes = 0
            game.is_top_inning = not game.is_top_inning
            if game.is_top_inning:
                game.current_inning += 1
            state["runners"] = {"1b": None, "2b": None, "3b": None}
            description += " Tres outs registrados. Cambio de entrada."

    state["runners"] = runners
    game.state_data = state

    db.commit()
    db.refresh(game)

    return {
        "status": "ok",
        "success": success,
        "description": description,
        "outs": game.outs,
        "runners": runners
    }