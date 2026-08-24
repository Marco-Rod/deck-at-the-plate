"""
Router: Motor de Jugabilidad 1v1
=================================
Gestiona el flujo completo de un at-bat en tiempo real:
  1. POST /{game_id}/play-tactic  → Activar carta táctica antes del enfrentamiento.
  2. POST /{game_id}/pitch        → El lanzador selecciona zona y tipo de tiro (Fase 1).
  3. POST /{game_id}/swing        → El bateador responde; el engine resuelve la jugada (Fase 2+3).
  4. POST /{game_id}/change-pitcher → Sustitución de picher desde el bullpen.
  5. POST /{game_id}/steal        → Intento de robo de base.

Flujo PvE (un solo jugador humano):
  - El humano es siempre el equipo HOME.
  - En la Alta (Top): la CPU pichea → el humano batea.
    select_pitch no aplica; trigger_cpu_response_if_needed se encarga del picheo.
  - En la Baja (Bottom): el humano pichea → trigger_cpu_response_if_needed ejecuta
    el swing de la CPU automáticamente tras confirmar el picheo humano.

Cada acción valida el turno del jugador autenticado (JWT) y emite actualizaciones en tiempo real
a ambos clientes conectados vía WebSocket.
"""

import random
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


def _apply_tactic_modifiers(active_tactics: dict, db: Session) -> dict:
    """
    Lee las cartas tácticas activas desde la DB y acumula sus modificadores.
    Retorna un dict listo para pasar a calculate_play_outcome().
    """
    mods = {"batter_con": 1.0, "batter_pwr": 1.0, "batter_vis": 1.0, "pitcher_mov": 1.0}

    if active_tactics.get("batter"):
        tac = db.query(TacticCard).filter(TacticCard.id == active_tactics["batter"]).first()
        if tac:
            for eff in tac.effects:
                attr = eff.get("attribute")
                val = eff.get("value", 0) / 100.0
                if attr == "vision":
                    mods["batter_vis"] += val
                elif attr == "contacto":
                    mods["batter_con"] += val
                elif attr == "poder":
                    mods["batter_pwr"] += val

    if active_tactics.get("pitcher"):
        tac = db.query(TacticCard).filter(TacticCard.id == active_tactics["pitcher"]).first()
        if tac:
            for eff in tac.effects:
                attr = eff.get("attribute")
                val = eff.get("value", 0) / 100.0
                if attr == "movimiento":
                    mods["pitcher_mov"] += val

    return mods


async def _resolve_swing(
    game: GameSession,
    state: dict,
    swing_type: str,
    guessed_zone: int | None,
    guessed_pitch: str | None,
    db: Session,
    game_id: str,
) -> tuple[str, str]:
    """
    Núcleo compartido entre execute_swing (humano) y la CPU en PvE.

    Ejecuta los pasos 1-6 del at-bat: fatiga, tácticas, cálculo, transición
    y broadcast WS. Persiste el estado y retorna (event, description).

    Args:
        game:          Instancia de GameSession (será mutada).
        state:         state_data mutable del juego.
        swing_type:    'NORMAL', 'POWER', 'TAKE' o 'BUNT'.
        guessed_zone:  Zona que el bateador intenta adivinar (1-9 o None).
        guessed_pitch: Tipo de lanzamiento adivinado o None.
        db:            Sesión de base de datos activa.
        game_id:       ID de la partida para el broadcast WS.
    """
    current_pitch = state.get("current_pitch") or {}

    # --- 1. Fatiga del pitcher ---
    pitch_counts = state.get("pitch_counts", {})
    active_pitcher_id = state.get("active_pitcher")
    active_batter_id = state.get("active_batter")

    current_count = pitch_counts.get(active_pitcher_id, 0) + 1
    pitch_counts[active_pitcher_id] = current_count
    state["pitch_counts"] = pitch_counts

    # --- 2. Obtener atributos reales desde la DB ---
    pitcher_card = db.query(PlayerCardModel).filter(PlayerCardModel.id == active_pitcher_id).first() if active_pitcher_id else None
    batter_card = db.query(PlayerCardModel).filter(PlayerCardModel.id == active_batter_id).first() if active_batter_id else None

    raw_pitcher_attrs = map_card_to_pitcher_attrs(pitcher_card) if pitcher_card else {"velocidad": 75, "control": 70, "movimiento": 70}
    batter_attrs = map_card_to_batter_attrs(batter_card) if batter_card else {"contacto": 70, "poder": 70, "vision": 70}
    pitcher_attrs = apply_pitcher_fatigue(raw_pitcher_attrs, current_count)

    # --- NUEVO: Extraer estadísticas específicas del picheo lanzado desde el repertorio ---
    selected_pitch_type = current_pitch.get("pitch_type", "4-SEAM")
    pitch_specific_stats = pitcher_card.get_pitch_stats(selected_pitch_type) if pitcher_card else None


    if pitch_specific_stats:
        # Enriquecemos current_pitch con los datos reales del repertorio para calculator.py
        current_pitch["velocity"] = pitch_specific_stats.get("velocity", pitcher_attrs["velocidad"])
        current_pitch["control"] = pitch_specific_stats.get("control", pitcher_attrs["control"])
        current_pitch["movement"] = pitch_specific_stats.get("movement", pitcher_attrs["movimiento"])
    active_tactics = state.get("active_tactics", {})

    # --- 3. Procesamiento especial de BUNT ---
    if swing_type == "BUNT":
        raw_event, description, sac_success = resolve_bunt(pitcher_attrs, batter_attrs, state.get("runners", {}))
        if sac_success and any(state.get("runners", {}).values()):
            runners = state.get("runners", {})
            new_runners = {"1b": None, "2b": None, "3b": None}
            if runners.get("2b"):
                new_runners["3b"] = runners["2b"]
            if runners.get("1b"):
                new_runners["2b"] = runners["1b"]
            state["runners"] = new_runners
    else:
        # --- 4. Modificadores de cartas tácticas ---
        tactics_modifiers = _apply_tactic_modifiers(active_tactics, db)

        # --- 5. Calcular resultado ---
        raw_event, description = calculate_play_outcome(
            pitcher_attrs=pitcher_attrs,
            batter_attrs=batter_attrs,
            pitch_selected=current_pitch,
            swing_selected={
                "swing_type": swing_type,
                "guessed_zone": guessed_zone,
                "guessed_pitch": guessed_pitch,
            },
            tactics_modifiers=tactics_modifiers,
        )

    # --- 6. Transición de estado ---
    at_bat_ended, inning_ended, event = process_at_bat_transition(game, raw_event, state)

    if event == "STRIKEOUT":
        description = "¡Tercer strike! Bateador ponchado."
    elif event == "WALK":
        description = "Cuatro bolas malas. Bateador toma base por bolas."
    if inning_ended:
        description += " Tres outs registrados. Cambio de entrada."

    # --- 7. Persistir y hacer broadcast ---
    state["current_pitch"] = None
    state["last_event"] = event
    game.state_data = state

    db.commit()
    db.refresh(game)

    await manager.broadcast_to_game(game_id, _build_play_resolved_payload(game, event, description))
    return event, description


def _is_cpu_turn(game: GameSession, state: dict, required_role: str) -> bool:
    """
    Determina si en este momento le toca actuar a la CPU.

    En modo PvE el humano es siempre HOME:
      - Top inning  → CPU (away) está pitcheando, humano batea.
      - Bot inning  → Humano (home) pichea, CPU (away) batea.

    Args:
        required_role: 'PITCHER' o 'BATTER' — el rol que se está evaluando.
    """
    if state.get("mode") != "PVE":
        return False
    if game.away_user_id != "CPU_BOT":
        return False

    # En la Alta (top) la visita batea y el local pichea.
    # En la Baja (bot) el local batea y la visita pichea.
    if required_role == "PITCHER":
        return not game.is_top_inning  # CPU pichea solo en la baja (si es away)
    if required_role == "BATTER":
        return game.is_top_inning      # CPU batea en la alta

    return False


async def trigger_cpu_response_if_needed(game: GameSession, state: dict, db: Session, game_id: str) -> None:
    """
    En partidas PvE, evalúa si le toca actuar a la CPU y ejecuta su acción.

    Se llama al final de select_pitch y execute_swing (cuando el juego no terminó).

    Casos:
      A. El humano acaba de pichear (Bot inning):
         → La CPU elige su swing y se resuelve la jugada completa.

      B. El humano acaba de completar un at-bat como bateador (Top inning,
         o justo cambió la media entrada y la CPU debe pichear primero):
         → La CPU selecciona su picheo y emite PITCH_COMMITTED.
         → El siguiente ciclo (cuando el humano haga swing) completará la jugada.
    """
    if state.get("mode") != "PVE" or state.get("is_game_over"):
        return

    difficulty = state.get("difficulty", "MEDIUM")

    # Caso A: la CPU debe batear (hay un picheo humano pendiente)
    # Ocurre en el Bot inning cuando el humano (home) acaba de pichear.
    if _is_cpu_turn(game, state, "BATTER") and state.get("current_pitch"):
        cpu_swing = get_cpu_swing_action(difficulty)

        await _resolve_swing(
            game=game,
            state=state,
            swing_type=cpu_swing["swing_type"],
            guessed_zone=cpu_swing.get("guessed_zone"),
            guessed_pitch=cpu_swing.get("guessed_pitch"),
            db=db,
            game_id=game_id,
        )
        # Tras el swing de la CPU puede haber cambiado la media entrada.
        # Si ahora le toca lanzar a la CPU (nueva Alta), generar el picheo.
        state = dict(game.state_data or {})
        if state.get("is_game_over"):
            return

    # Caso B: la CPU debe pichear (no hay picheo pendiente y es el turno de la CPU)
    if _is_cpu_turn(game, state, "PITCHER") and not state.get("current_pitch"):
        cpu_pitch = get_cpu_pitch_action(difficulty)
        state["current_pitch"] = cpu_pitch
        game.state_data = state
        db.commit()

        await manager.broadcast_to_game(game_id, {
            "type": "PITCH_COMMITTED",
            "message": "La CPU ha seleccionado su picheo. Es tu turno de batear.",
            "has_pitched": True,
        })


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

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
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión de juego no encontrada.")

    tactic = db.query(TacticCard).filter(TacticCard.id == payload.tactic_id).first()
    if not tactic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carta táctica no encontrada.")

    state = dict(game.state_data or {})

    # En la Alta batea el visitante; en la Baja batea el local.
    if payload.player_role.upper() == "BATTER":
        player_key = "away" if game.is_top_inning else "home"
    else:
        player_key = "home" if game.is_top_inning else "away"

    tactics_data = state.get("tactics", {}).get(player_key, {})
    player_hand = tactics_data.get("hand", [])

    if payload.tactic_id not in player_hand:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La carta seleccionada no se encuentra en la mano actual del jugador."
        )

    if tactic.category == "EXTRA_INNINGS" and game.current_inning < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La carta '{tactic.name}' solo se puede activar en extra innings (Entrada 10+)."
        )

    active_tactics = state.get("active_tactics", {"home": None, "away": None})
    role_key = "pitcher" if payload.player_role.upper() == "PITCHER" else "batter"
    active_tactics[role_key] = tactic.id
    state["active_tactics"] = active_tactics

    discard_used_tactic(state["tactics"], player_key, payload.tactic_id)

    game.state_data = state
    db.commit()

    return {"status": "ok", "message": f"Táctica '{tactic.name}' activada para este enfrentamiento."}


@router.post("/{game_id}/pitch", summary="Registrar picheo (Fase 1)")
async def select_pitch(
    game_id: str,
    payload: PitchActionRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Guarda la selección secreta del lanzador (tipo de tiro y zona 1-9) en state_data.
    El bateador no puede ver esta información gracias al Fog of War en GET /{game_id}.

    En PvE, tras registrar el picheo del jugador humano (Bot inning), la CPU ejecuta
    su swing automáticamente y resuelve la jugada completa.
    """
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    verify_player_turn(game, current_user_id, required_role="PITCHER")

    state = dict(game.state_data or {})
    active_pitcher_id = state.get("active_pitcher")
    if active_pitcher_id:
        pitcher_card = db.query(PlayerCardModel).filter(PlayerCardModel.id == active_pitcher_id).first()
        if pitcher_card and payload.pitch_type != "IBB":
            pitch_stats = pitcher_card.get_pitch_stats(payload.pitch_type)
            if not pitch_stats:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El lanzador {pitcher_card.name} no tiene el picheo '{payload.pitch_type}' en su repertorio."
                )
                
    state["current_pitch"] = {
        "pitch_type": payload.pitch_type,
        "zone": payload.zone,
    }
    game.state_data = state
    db.commit()

    await manager.broadcast_to_game(game_id, {
        "type": "PITCH_COMMITTED",
        "message": "El lanzador ha ejecutado su picheo. Esperando swing del bateador.",
        "has_pitched": True,
    })

    # En PvE: si la CPU es la bateadora en este momento, ejecuta su swing ahora.
    state = dict(game.state_data or {})
    if not state.get("is_game_over"):
        await trigger_cpu_response_if_needed(game, state, db, game_id)

    return {"status": "ok", "message": "Picheo registrado exitosamente."}


@router.post("/{game_id}/swing", response_model=PlayResultResponse, summary="Ejecutar swing y resolver jugada (Fase 2 y 3)")
async def execute_swing(
    game_id: str,
    payload: SwingActionRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Procesa la acción del bateador y resuelve la jugada completa.

    Pasos internos:
      1. Fatiga del pitcher.
      2. Modificadores de cartas tácticas.
      3. Cálculo del resultado con el motor Statcast.
      4. Transición de estado (conteo, corredores, marcador, lineup, inning).
      5. Broadcast PLAY_RESOLVED vía WebSocket.

    En PvE, tras resolver la jugada del humano, la CPU genera su picheo
    automáticamente si le corresponde pichear en la siguiente media entrada.
    """
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    verify_player_turn(game, current_user_id, required_role="BATTER")

    state = dict(game.state_data or {})
    if not state.get("current_pitch"):
        raise HTTPException(status_code=400, detail="El lanzador aún no ha realizado su picheo para este turno.")

    event, description = await _resolve_swing(
        game=game,
        state=state,
        swing_type=payload.swing_type,
        guessed_zone=payload.guessed_zone,
        guessed_pitch=payload.guessed_pitch,
        db=db,
        game_id=game_id,
    )

    # En PvE: si la CPU debe pichear en la siguiente media entrada, lo hace ahora.
    state = dict(game.state_data or {})
    if not state.get("is_game_over"):
        await trigger_cpu_response_if_needed(game, state, db, game_id)

    return _build_play_result_response(game, event, description)


@router.post("/{game_id}/change-pitcher", summary="Realizar cambio de relevista (Bullpen)")
def change_pitcher(game_id: str, payload: ChangePitcherRequest, db: Session = Depends(get_db)):
    """
    Sustituye al lanzador activo por un relevista del bullpen.
    Valida que la carta exista y corresponda a un rol de pitcheo (SP, RP o TWP).
    Inicializa en cero el contador de lanzamientos del entrante.
    """
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

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
        "active_pitcher": payload.new_pitcher_id,
    }


@router.post("/{game_id}/steal", summary="Intentar robo de base")
async def steal_base(game_id: str, payload: StealBaseRequest, db: Session = Depends(get_db)):
    """
    Ejecuta un intento de robo de base (2B o 3B) por parte del equipo ofensivo.
    La probabilidad de éxito depende de los atributos del pitcher activo.
    Si el corredor es out, se registra el out, se evalúa cambio de entrada
    y se verifica la condición de fin de juego.
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
            state["just_switched_half"] = True
            state["runners"] = {"1b": None, "2b": None, "3b": None}
            game.is_top_inning = not game.is_top_inning
            if game.is_top_inning:
                game.current_inning += 1
            description += " Tres outs registrados. Cambio de entrada."

            # Verificar fin de juego tras el out por robo
            from app.engine.game_over_manager import check_game_over
            is_over, win_msg = check_game_over(game, state)
            if is_over:
                state["is_game_over"] = True
                state["winner_message"] = win_msg
        else:
            state["just_switched_half"] = False

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
        "state_data": game.state_data,
    })

    return {
        "status": "ok",
        "success": success,
        "description": description,
        "outs": game.outs,
        "runners": runners,
    }


