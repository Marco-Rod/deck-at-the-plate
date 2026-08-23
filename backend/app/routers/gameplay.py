"""
Router: Motor de Jugabilidad 1v1
=================================
Gestiona el flujo completo de un at-bat en tiempo real:
  1. POST /{game_id}/play-tactic  → Activar carta táctica antes del enfrentamiento.
  2. POST /{game_id}/pitch        → El lanzador selecciona zona y tipo de tiro (Fase 1).
  3. POST /{game_id}/swing        → El bateador responde; el engine resuelve la jugada (Fase 2+3).
  4. POST /{game_id}/change-pitcher → Sustitución de picher desde el bullpen.
  5. POST /{game_id}/steal        → Intento de robo de base.

Cada acción valida el turno del jugador autenticado (JWT) y emite actualizaciones en tiempo real
a ambos clientes conectados vía WebSocket.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.auth import get_current_user
from app.database import get_db
from app.models import GameSession, PlayerCardModel, TacticCard
from app.schemas import (
    PlayTacticRequest,
    PitchActionRequest,
    SwingActionRequest,
    PlayResultResponse,
    ChangePitcherRequest,
    StealBaseRequest,
)
from app.engine.calculator import calculate_play_outcome
from app.engine.state_manager import process_at_bat_transition
from app.engine.fatigue_manager import apply_pitcher_fatigue
from app.engine.deck_manager import discard_used_tactic
from app.engine.tactical_actions import resolve_bunt, resolve_steal
from app.engine.websocket_manager import manager
from app.engine.turn_guard import verify_player_turn
from app.engine.cpu_ai import get_cpu_pitch_action, get_cpu_swing_action
from app.engine.attribute_mapper import map_card_to_pitcher_attrs, map_card_to_batter_attrs

router = APIRouter(prefix="/api/v1/games", tags=["Motor de Jugabilidad 1v1"])


@router.post("/{game_id}/play-tactic", summary="Activar carta táctica")
def play_tactic(game_id: str, payload: PlayTacticRequest, db: Session = Depends(get_db)):
    """
    Registra el uso de una carta táctica para el turno actual en state_data.
    La carta se mueve de la mano al descarte y sus efectos quedan pendientes de aplicar
    hasta que se resuelva el swing.

    Restricciones:
    - La carta debe estar en la mano del jugador.
    - Las cartas de categoría EXTRA_INNINGS solo son válidas a partir del inning 10.
    """
    # --- Paso 1: Queries a la base de datos ---
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión de juego no encontrada."
        )

    tactic = db.query(TacticCard).filter(TacticCard.id == payload.tactic_id).first()
    if not tactic:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Carta táctica no encontrada."
        )

    # --- Paso 2: Leer estado del juego ---
    state = dict(game.state_data or {})

    # Determinar a qué equipo pertenece el jugador según su rol y la media entrada actual
    # En la Alta batea el visitante; en la Baja batea el local.
    if payload.player_role.upper() == "BATTER":
        player_key = "away" if game.is_top_inning else "home"
    else:  # PITCHER
        player_key = "home" if game.is_top_inning else "away"

    # --- Paso 3: Validar que la carta esté en la mano ---
    tactics_data = state.get("tactics", {}).get(player_key, {})
    player_hand = tactics_data.get("hand", [])

    if payload.tactic_id not in player_hand:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La carta seleccionada no se encuentra en la mano actual del jugador."
        )

    # --- Paso 4: Restricción de Inning para cartas de Extra Innings ---
    if tactic.category == "EXTRA_INNINGS" and game.current_inning < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La carta '{tactic.name}' solo se puede activar en extra innings (Entrada 10+)."
        )

    # --- Paso 5: Registrar táctica activa y mover carta al descarte ---
    active_tactics = state.get("active_tactics", {"home": None, "away": None})
    role_key = "pitcher" if payload.player_role.upper() == "PITCHER" else "batter"
    active_tactics[role_key] = tactic.id
    state["active_tactics"] = active_tactics

    discard_used_tactic(state["tactics"], player_key, payload.tactic_id)

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
    Guarda la selección secreta del lanzador (tipo de tiro y zona 1-9) en state_data.
    El bateador no puede ver esta información gracias al Fog of War aplicado en GET /{game_id}.

    Una vez registrado, emite PITCH_COMMITTED vía WebSocket para que el bateador sepa
    que puede ejecutar su swing.
    """
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    verify_player_turn(game, current_user_id, required_role="PITCHER")

    state = dict(game.state_data or {})
    state["current_pitch"] = {
        "pitch_type": payload.pitch_type,
        "zone": payload.zone
    }

    game.state_data = state
    db.commit()

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
    Punto central del engine. Procesa la acción del bateador en tres pasos:

    1. Fatiga: incrementa el contador de lanzamientos del pitcher y degrada sus atributos
       si superó el umbral de 60 envíos.
    2. Tácticas: aplica los modificadores de las cartas activas sobre los atributos base.
    3. Resolución: calcula el resultado (STRIKE, BALL, HIT, OUT, HOME_RUN, etc.) con el
       motor matemático basado en Statcast + RNG ponderado.
    4. Transición: actualiza conteo, corredores, marcador, rotación de lineup e inning.
    5. Broadcast: emite PLAY_RESOLVED vía WebSocket con el estado completo.
    """
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    verify_player_turn(game, current_user_id, required_role="BATTER")

    state = dict(game.state_data or {})
    current_pitch = state.get("current_pitch")

    if not current_pitch:
        raise HTTPException(
            status_code=400,
            detail="El lanzador aún no ha realizado su picheo para este turno."
        )

    # --- 1. Fatiga del pitcher ---
    pitch_counts = state.get("pitch_counts", {})
    active_pitcher_id = state.get("active_pitcher")
    active_batter_id = state.get("active_batter")

    current_count = pitch_counts.get(active_pitcher_id, 0) + 1
    pitch_counts[active_pitcher_id] = current_count
    state["pitch_counts"] = pitch_counts

    # --- 2. Obtener atributos reales de las cartas desde la DB ---
    pitcher_card = db.query(PlayerCardModel).filter(PlayerCardModel.id == active_pitcher_id).first() if active_pitcher_id else None
    batter_card = db.query(PlayerCardModel).filter(PlayerCardModel.id == active_batter_id).first() if active_batter_id else None

    # map_card_to_*_attrs convierte columnas del modelo (inglés) al dict que espera el engine (español)
    raw_pitcher_attrs = map_card_to_pitcher_attrs(pitcher_card) if pitcher_card else {"velocidad": 75, "control": 70, "movimiento": 70}
    batter_attrs = map_card_to_batter_attrs(batter_card) if batter_card else {"contacto": 70, "poder": 70, "vision": 70}

    # Aplicar degradación por fatiga sobre los atributos del pitcher
    pitcher_attrs = apply_pitcher_fatigue(raw_pitcher_attrs, current_count)

    # --- 3. Procesamiento de bunt (antes de calcular tácticas) ---
    active_tactics = state.get("active_tactics", {})
    tactics_modifiers = {"batter_con": 1.0, "batter_pwr": 1.0, "batter_vis": 1.0, "pitcher_mov": 1.0}

    if payload.swing_type == "BUNT":
        raw_event, description, sac_success = resolve_bunt(pitcher_attrs, batter_attrs, state.get("runners", {}))

        if sac_success and any(state.get("runners", {}).values()):
            runners = state.get("runners", {})
            new_runners = {"1b": None, "2b": None, "3b": None}
            if runners.get("2b"):
                new_runners["3b"] = runners["2b"]
            if runners.get("1b"):
                new_runners["2b"] = runners["1b"]
            state["runners"] = new_runners

        # El bunt ya tiene su evento resuelto; saltar al paso de transición
        at_bat_ended, inning_ended, event = process_at_bat_transition(game, raw_event, state)
        state["current_pitch"] = None
        state["last_event"] = event
        game.state_data = state
        db.commit()
        db.refresh(game)

        await manager.broadcast_to_game(game_id, _build_play_resolved_payload(game, event, description))
        return _build_play_result_response(game, event, description)

    # --- 4. Modificadores de cartas tácticas activas ---
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

    # --- 5. Calcular resultado mediante el motor matemático ---
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

    # --- 6. Transición de estado ---
    at_bat_ended, inning_ended, event = process_at_bat_transition(game, raw_event, state)

    if event == "STRIKEOUT":
        description = "¡Tercer strike! Bateador ponchado."
    elif event == "WALK":
        description = "Cuatro bolas malas. Bateador toma base por bolas."
    if inning_ended:
        description += " Tres outs registrados. Cambio de entrada."

    # --- 7. Limpiar picheo procesado y persistir ---
    state["current_pitch"] = None
    state["last_event"] = event
    game.state_data = state

    db.commit()
    db.refresh(game)

    await manager.broadcast_to_game(game_id, _build_play_resolved_payload(game, event, description))
    return _build_play_result_response(game, event, description)


@router.post("/{game_id}/change-pitcher", summary="Realizar cambio de relevista (Bullpen)")
def change_pitcher(game_id: str, payload: ChangePitcherRequest, db: Session = Depends(get_db)):
    """
    Sustituye al lanzador activo por un relevista del bullpen.
    Valida que la carta exista y corresponda a un rol de pitcheo (SP o RP).
    Inicializa en cero el contador de lanzamientos del entrante.
    """
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    # Usar PlayerCardModel (correcto) y validar por campo 'position' en lugar de 'role' inexistente
    new_pitcher = db.query(PlayerCardModel).filter(PlayerCardModel.id == payload.new_pitcher_id).first()
    if not new_pitcher or new_pitcher.position not in ("SP", "RP", "TWP"):
        raise HTTPException(
            status_code=400,
            detail="La carta indicada no corresponde a un lanzador válido (SP, RP o TWP)."
        )

    state = dict(game.state_data or {})
    state["active_pitcher"] = payload.new_pitcher_id

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
    Ejecuta un intento de robo de base (2B o 3B) por parte del equipo ofensivo.
    La probabilidad de éxito depende de los atributos del pitcher activo (velocidad/control).
    Si el corredor es out, se registra el out y se evalúa si corresponde cambio de entrada.
    """
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    state = dict(game.state_data or {})
    active_pitcher_id = state.get("active_pitcher")

    pitcher_card = db.query(PlayerCardModel).filter(PlayerCardModel.id == active_pitcher_id).first() if active_pitcher_id else None
    pitcher_attrs = map_card_to_pitcher_attrs(pitcher_card) if pitcher_card else {"velocidad": 75, "control": 70, "movimiento": 70}

    runners = state.get("runners", {"1b": None, "2b": None, "3b": None})
    success, description = resolve_steal(pitcher_attrs, runners, payload.target_base)

    from_base = "1b" if payload.target_base == "2b" else "2b"

    if success:
        runners[payload.target_base] = runners[from_base]
        runners[from_base] = None
    else:
        # Out por robo fallido (Caught Stealing)
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

    await manager.broadcast_to_game(game_id, {
        "type": "STEAL_RESOLVED",
        "success": success,
        "description": description,
        "outs": game.outs,
        "runners": runners,
        "current_inning": game.current_inning,
        "is_top_inning": game.is_top_inning,
    })

    return {
        "status": "ok",
        "success": success,
        "description": description,
        "outs": game.outs,
        "runners": runners
    }


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _build_play_resolved_payload(game: GameSession, event: str, description: str) -> dict:
    """Construye el payload estándar de WebSocket para PLAY_RESOLVED."""
    return {
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
        "state_data": game.state_data,
    }


def _build_play_result_response(game: GameSession, event: str, description: str) -> PlayResultResponse:
    """Construye el PlayResultResponse estándar para la respuesta HTTP."""
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
        state_data=game.state_data,
    )


async def trigger_cpu_response_if_needed(game: GameSession, db: Session):
    """
    Evalúa si el turno actual le corresponde a la CPU (modo PVE).
    Si la CPU debe pichear, genera y registra su lanzamiento automáticamente.
    Si la CPU debe batear (el humano ya pichó), ejecuta su swing internamente.

    Este método debe llamarse al final de `select_pitch` y `execute_swing`
    en partidas PVE para mantener el flujo de juego continuo.
    """
    state = dict(game.state_data or {})
    if state.get("mode") != "PVE":
        return

    difficulty = state.get("difficulty", "MEDIUM")

    cpu_is_pitching = (
        (game.is_top_inning and game.home_user_id == "CPU_BOT") or
        (not game.is_top_inning and game.away_user_id == "CPU_BOT")
    )

    if cpu_is_pitching and not state.get("current_pitch"):
        cpu_pitch = get_cpu_pitch_action(difficulty)
        state["current_pitch"] = cpu_pitch
        game.state_data = state
        db.commit()

        await manager.broadcast_to_game(game.id, {
            "type": "PITCH_COMMITTED",
            "message": "La CPU ha seleccionado su picheo.",
            "has_pitched": True
        })

    elif not cpu_is_pitching and state.get("current_pitch"):
        # El swing de la CPU se maneja construyendo el payload y reutilizando la lógica del engine.
        # TODO: Extraer lógica de execute_swing a una función interna para invocarla aquí.
        pass
