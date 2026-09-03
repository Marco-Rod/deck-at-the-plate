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
    select_pitch no aplica; trigger_cpu_response se encarga del picheo.
  - En la Baja (Bottom): el humano pichea → trigger_cpu_response ejecuta
    el swing de la CPU automáticamente tras confirmar el picheo humano.

Cada acción valida el turno del jugador autenticado (JWT) y emite actualizaciones en tiempo real
a ambos clientes conectados vía WebSocket.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.auth import get_current_user
from app.database import get_db
from app.models import GameSession
from app.schemas import (
    PlayTacticRequest,
    PitchActionRequest,
    SwingActionRequest,
    PlayResultResponse,
    ChangePitcherRequest,
    StealBaseRequest,
)
from app.engine.websocket_manager import manager
from app.engine.fog_of_war import sanitize_state_for_player
from app.engine.game_rules import EXTRA_INNINGS_MIN_INNING
from app.engine.turn_guard import expected_actor, is_player_turn
from app.engine.cpu_ai import is_cpu_turn
from app.engine.attribute_mapper import map_card_to_pitcher_attrs
from app.engine.game_actions import resolve_swing, trigger_cpu_response
from app.engine.bullpen import (
    acknowledge_pending_pitcher_change,
    apply_human_pitcher_change,
    list_rival_available_pitchers,
    list_user_available_pitchers,
)
from app.engine.steal_actions import steal_attempt
from app.engine.tactical_actions import activate_tactic
from app.repositories import get_card_by_id, get_game_by_id, get_tactic_card_by_id
from app.services.card_presenter import build_pitcher_payload

router = APIRouter(prefix="/api/v1/games", tags=["Motor de Jugabilidad 1v1"])

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _require_turn(game: GameSession, current_user_id: str, required_role: str) -> None:
    """
    Valida el turno del usuario traduciendo la decisión pura de turn_guard a HTTP.
    """
    if expected_actor(game, required_role) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rol de juego no válido.",
        )
    if not is_player_turn(game, current_user_id, required_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"No es tu turno. Se esperaba la acción del usuario con rol {required_role}. "
                f"user_id={current_user_id}, is_top={game.is_top_inning}"
            ),
        )



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


def _player_state_for(game: GameSession, requesting_user_id: str) -> dict:
    """State_data de la partida sanitizado (Fog of War) para un destinatario concreto."""
    return sanitize_state_for_player(
        state_data=game.state_data,
        requesting_user_id=requesting_user_id,
        home_user_id=game.home_user_id,
        away_user_id=game.away_user_id,
        is_top_inning=game.is_top_inning,
    )



# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/{game_id}/play-tactic", summary="Activar carta táctica")
def play_tactic(
    game_id: str,
    payload: PlayTacticRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Registra el uso de una carta táctica para el turno actual en state_data.
    La carta se mueve de la mano al descarte y sus efectos quedan pendientes de aplicar
    hasta que se resuelva el swing.

    Restricciones:
    - La carta debe estar en la mano del jugador.
    - Las cartas de categoría EXTRA_INNINGS solo son válidas a partir del inning 10.
    """
    game = get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión de juego no encontrada.")

    # Solo usuarios involucrados pueden jugar tácticas.
    if current_user_id not in (game.home_user_id, game.away_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes acceso a esta partida.")

    # La táctica se activa para el rol y el turno actual del solicitante.
    _require_turn(game, current_user_id, required_role=payload.player_role.upper())

    tactic = get_tactic_card_by_id(db, payload.tactic_id)
    if not tactic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carta táctica no encontrada.")

    state = dict(game.state_data or {})

    # Regla de dominio (turno, mano, extra innings) en el engine puro.
    ok, error_code = activate_tactic(
        state,
        player_role=payload.player_role,
        tactic_id=payload.tactic_id,
        tactic_category=tactic.category,
        current_inning=game.current_inning,
        is_top_inning=game.is_top_inning,
    )
    if not ok:
        if error_code == "extra_innings":
            detail = f"La carta '{tactic.name}' solo se puede activar en extra innings (Entrada {EXTRA_INNINGS_MIN_INNING}+)."
        elif error_code == "invalid_role":
            detail = "player_role debe ser 'PITCHER' o 'BATTER'."
        else:
            detail = "La carta seleccionada no se encuentra en la mano actual del jugador."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

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
    # ⭐ DEBUG: Verificar que los datos llegan correctamente
    logger.debug(
        "Endpoint /pitch recibio: game_id=%s pitch_type=%s zone=%s user_id=%s",
        game_id, payload.pitch_type, payload.zone, current_user_id,
    )
    
    game = get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    # ⭐ NUEVO: Validar que no haya cambio de pitcher pendiente
    state = dict(game.state_data or {})
    if state.get("awaiting_pitcher_change_acknowledgment"):
        logger.warning("Pitch bloqueado: cambio de pitcher del rival pendiente de confirmacion")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El rival cambió de pitcher. Debes confirmar el cambio antes de continuar.",
        )

    _require_turn(game, current_user_id, required_role="PITCHER")
    active_pitcher_id = state.get("active_pitcher")
    
    logger.debug("active_pitcher_id: %s", active_pitcher_id)
    
    if active_pitcher_id:
        pitcher_card = get_card_by_id(db, active_pitcher_id)
        logger.debug("pitcher_card: %s", pitcher_card.name if pitcher_card else "NOT FOUND")
        
        if pitcher_card and payload.pitch_type != "IBB":
            # Validar que existe en repertorio
            pitch_stats = pitcher_card.get_pitch_stats(payload.pitch_type)
            logger.debug("pitch_stats para '%s': %s", payload.pitch_type, pitch_stats)
            
            if not pitch_stats:
                logger.warning("El lanzador %s no tiene '%s' en repertorio", pitcher_card.name, payload.pitch_type)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El lanzador {pitcher_card.name} no tiene el picheo '{payload.pitch_type}' en su repertorio."
                )
            
            # ⭐ Validar que no exceda máximo de 4 pitcheos
            if not pitcher_card.validate_repertoire():
                logger.warning("Repertorio inválido para %s", pitcher_card.name)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El lanzador {pitcher_card.name} tiene un repertorio inválido (máximo 4 pitcheos únicos)."
                )
                
    state["current_pitch"] = {
        "pitch_type": payload.pitch_type,
        "zone": payload.zone,
    }
    game.state_data = state
    db.commit()
    logger.debug("State guardado con pitch: %s", state["current_pitch"])

    await manager.broadcast_to_game(game_id, {
        "type": "PITCH_COMMITTED",
        "message": "El lanzador ha ejecutado su picheo. Esperando swing del bateador.",
        "has_pitched": True,
    })

    # En PvE: si la CPU es la bateadora en este momento, ejecuta su swing ahora.
    state = dict(game.state_data or {})
    if not state.get("is_game_over"):
        await trigger_cpu_response(game, state, db, game_id)
        # La CPU pudo batear/pichear sin commitear: persistir la transacción completa.
        db.commit()

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
    logger.debug("DEBUG swing: game_id=%s, user_id=%s", game_id, current_user_id)
    
    game = get_game_by_id(db, game_id)
    if not game:
        logger.warning("ERROR: Juego no encontrado: %s", game_id)
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    logger.debug(
        "home_user_id=%s, away_user_id=%s, is_top_inning=%s",
        game.home_user_id, game.away_user_id, game.is_top_inning,
    )
    
    _require_turn(game, current_user_id, required_role="BATTER")

    # ⭐ NUEVO: Expulsar todas las sesiones cacheadas y obtener una fresca de la BD
    db.expunge_all()
    game = get_game_by_id(db, game_id)
    db.refresh(game)
    state = dict(game.state_data or {})
    
    # ⭐ NUEVO: Validar que no haya cambio de pitcher pendiente
    if state.get("awaiting_pitcher_change_acknowledgment"):
        logger.warning("Swing bloqueado: cambio de pitcher del rival pendiente de confirmacion")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El rival cambió de pitcher. Debes confirmar el cambio antes de continuar.",
        )
    
    current_pitch = state.get("current_pitch")
    
    # ⭐ CRÍTICO: Si no hay picheo y debería haber CPU pitcher, ejecutar CPU response aquí
    if not current_pitch:
        logger.debug("No hay pitch. Verificando si CPU deberia haber lanzado...")
        
        if is_cpu_turn(game, state, "PITCHER"):
            logger.debug("CPU deberia haber lanzado! Ejecutando trigger ahora...")
            await trigger_cpu_response(game, state, db, game_id)
            # La CPU pudo pichear/cambiar pitcher sin commitear: persistir antes de recargar.
            db.commit()
            # Recargar state después de que CPU lance
            db.expunge_all()
            game = get_game_by_id(db, game_id)
            db.refresh(game)
            state = dict(game.state_data or {})
            current_pitch = state.get("current_pitch")
            logger.debug("Despues de trigger, current_pitch = %s", bool(current_pitch))
    
    if not current_pitch:
        logger.warning(
            "ERROR: No hay picheo previo en state: %s",
            {"keys": list(state.keys()), "is_top": game.is_top_inning,
             "active_pitcher": state.get("active_pitcher"), "mode": state.get("mode")},
        )
        raise HTTPException(status_code=400, detail="El lanzador aún no ha realizado su picheo para este turno.")

    logger.debug("Swing valido, resolviendo jugada...")
    event, description, inning_ended = await resolve_swing(
        game=game,
        state=state,
        swing_type=payload.swing_type,
        guessed_zone=payload.guessed_zone,
        guessed_pitch=payload.guessed_pitch,
        db=db,
        game_id=game_id,
        user_id=current_user_id,  # ⭐ NUEVO: pasar user_id
    )

    # En PvE: si la CPU debe pichear en la siguiente media entrada, lo hace ahora.
    state = dict(game.state_data or {})
    if not state.get("is_game_over"):
        await trigger_cpu_response(game, state, db, game_id)

    # Persistir la transacción completa (swing humano + picheo/cambio de la CPU).
    db.commit()
    db.refresh(game)

    return _build_play_result_response(game, event, description)


@router.post("/{game_id}/change-pitcher", summary="Realizar cambio de relevista (Bullpen)")
async def change_pitcher(
    game_id: str,
    payload: ChangePitcherRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Sustituye al lanzador activo por un relevista del bullpen.
    Actualiza home_pitcher_id / away_pitcher_id en state_data para que
    la transición de inning restaure el pitcher correcto.

    Seguridad: la identidad del usuario se deriva del JWT.
    """
    logger.debug("CHANGE_PITCHER: request recibido (game_id=%s, new_pitcher_id=%s)", game_id, payload.new_pitcher_id)

    game = get_game_by_id(db, game_id)
    if not game:
        logger.warning("CHANGE_PITCHER: juego NO encontrado: %s", game_id)
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    # Solo usuarios involucrados en la partida pueden hacer cambios.
    if current_user_id not in (game.home_user_id, game.away_user_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta partida.")

    state = dict(game.state_data or {})
    if state.get("awaiting_pitcher_change_acknowledgment"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hay un cambio de pitcher pendiente de confirmación.",
        )

    # Un jugador sólo puede hacer cambios mientras controla al pitcher. Esto
    # impide sustituir al rival o alterar el pitcher activo fuera de su turno.
    _require_turn(game, current_user_id, required_role="PITCHER")
    is_home_user = current_user_id == game.home_user_id
    own_pitcher_field = "home_pitcher_id" if is_home_user else "away_pitcher_id"
    if state.get("active_pitcher") != state.get(own_pitcher_field):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El lanzador activo no corresponde al lado del jugador actual.",
        )

    old_pitcher_id, error_detail = apply_human_pitcher_change(
        db,
        state,
        payload.new_pitcher_id,
        is_home_user,
        current_user_id,
    )
    if error_detail:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail)

    new_pitcher = get_card_by_id(db, payload.new_pitcher_id)
    old_pitcher = get_card_by_id(db, old_pitcher_id)

    logger.debug(
        "CHANGE_PITCHER: cambiando %s pitcher: %s (%s) -> %s (%s)",
        "HOME" if is_home_user else "AWAY",
        old_pitcher.name if old_pitcher else "OLD PITCHER", old_pitcher_id,
        new_pitcher.name, payload.new_pitcher_id,
    )

    game.state_data = state
    db.commit()
    db.refresh(game)

    # ⭐ Construir datos del nuevo pitcher para el cliente
    new_pitcher_data = build_pitcher_payload(
        new_pitcher,
        with_repertoire=True,
        with_stamina=True,
        pitch_count=0,
        fatigue_level=0.0,
    )

    logger.debug("PITCHER CHANGE: %s -> %s (%s)", old_pitcher_id, payload.new_pitcher_id, new_pitcher.name)

    # ⭐ NUEVO: Broadcast del cambio vía WebSocket (state_data sanitizado por destinatario)
    await manager.broadcast_to_game_view(game_id, lambda u: {
        "type": "PITCHER_CHANGED",
        "message": f"🔄 Cambio de picher. Entra a la loma: {new_pitcher.name}",
        "old_pitcher_id": old_pitcher_id,
        "new_pitcher_id": payload.new_pitcher_id,
        "new_pitcher": new_pitcher_data,
        "state_data": _player_state_for(game, u),
    })

    return {
        "status": "ok",
        "message": f"Cambio de pitcher completado. Entra a la loma: {new_pitcher.name}.",
        "active_pitcher_id": payload.new_pitcher_id,
        "active_pitcher": new_pitcher_data,
    }


@router.get("/{game_id}/rival-available-pitchers", summary="Obtener lanzadores disponibles del equipo rival")
def get_rival_available_pitchers(
    game_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Retorna los pitchers disponibles del equipo rival (CPU).
    Similar a get_available_pitchers pero para el lado contrario.
    
    Flujo:
      1. Obtener la sesión de juego
      2. Determinar qué equipo es el rival (CPU)
      3. Buscar todos los pitchers del team_id del rival
      4. Excluir el pitcher actualmente activo
      5. Retornar la lista
    """
    logger.debug("GET_RIVAL_AVAILABLE_PITCHERS: game_id=%s", game_id)

    game = get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    if current_user_id not in (game.home_user_id, game.away_user_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta partida.")

    state = dict(game.state_data or {})
    available_pitchers, error_message = list_rival_available_pitchers(
        db,
        state,
        user_is_home=current_user_id == game.home_user_id,
    )
    if error_message:
        return {
            "status": "error",
            "count": 0,
            "available_pitchers": [],
            "message": error_message,
        }

    return {
        "status": "ok",
        "count": len(available_pitchers),
        "available_pitchers": available_pitchers,
    }


@router.get("/{game_id}/available-pitchers", summary="Obtener lanzadores disponibles del bullpen")
def get_available_pitchers(
    game_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Retorna los pitchers disponibles en el bullpen del usuario (los que posee en inventario).
    Excluye el pitcher actualmente activo en el montículo.

    Seguridad: la identidad del usuario se deriva del JWT.
    """
    logger.debug("GET_AVAILABLE_PITCHERS: game_id=%s, user_id=%s", game_id, current_user_id)

    game = get_game_by_id(db, game_id)
    if not game:
        logger.warning("GET_AVAILABLE_PITCHERS: game not found: %s", game_id)
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    # ── Validar que el user del token corresponde a un jugador humano del juego ────
    if current_user_id not in (game.home_user_id, game.away_user_id):
        logger.warning(
            "GET_AVAILABLE_PITCHERS: user %s not in game (home=%s, away=%s)",
            current_user_id, game.home_user_id, game.away_user_id,
        )
        raise HTTPException(status_code=403, detail="El usuario no pertenece a este juego.")

    if current_user_id == "CPU_BOT":
        logger.warning("GET_AVAILABLE_PITCHERS: CPU_BOT cannot change pitcher")
        raise HTTPException(status_code=400, detail="El CPU no puede cambiar pitcher manualmente.")

    state = dict(game.state_data or {})
    available_pitchers = list_user_available_pitchers(db, state, current_user_id)

    return {
        "status": "ok",
        "count": len(available_pitchers),
        "available_pitchers": available_pitchers,
    }


@router.post("/{game_id}/acknowledge-pitcher-change", summary="Confirmar cambio de pitcher del rival")
async def acknowledge_pitcher_change(
    game_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    El usuario confirma que vio y aceptó el cambio de pitcher de la CPU.
    
    Esto desbloqueará el juego para que continúe. Si se llama sin que haya
    un cambio pendiente, retorna un error.
    """
    game = get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    if current_user_id not in (game.home_user_id, game.away_user_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta partida.")
    
    state = dict(game.state_data or {})
    
    # Capturar el cambio pendiente ANTES de confirmarlo: acknowledge_pending_pitcher_change
    # setea pending_pitcher_change a None, así que ya no se puede leer después.
    pending = state.get("pending_pitcher_change") or {}
    
    if not acknowledge_pending_pitcher_change(state):
        logger.debug("ACK PITCHER CHANGE: no hay cambio pendiente para confirmar")
        return {
            "status": "ok",
            "message": "No hay cambio de pitcher pendiente",
        }
    
    logger.debug(
        "ACK PITCHER CHANGE: usuario confirmo cambio de pitcher (old=%s new=%s)",
        pending.get("old_pitcher_id"),
        pending.get("new_pitcher_id"),
    )
    
    game.state_data = state
    db.commit()
    db.refresh(game)
    
    # Broadcast para notificar que se desbloqueó (state_data sanitizado por destinatario)
    try:
        await manager.broadcast_to_game_view(game_id, lambda u: {
            "type": "PITCHER_CHANGE_ACKNOWLEDGED",
            "message": "El juego continúa. El nuevo pitcher está listo.",
            "state_data": _player_state_for(game, u),
        })
    except Exception as e:  # noqa: BLE001 - el broadcast no debe romper el flujo
        logger.warning("No se pudo emitir el broadcast de ack de cambio de pitcher: %s", e)
    
    return {
        "status": "ok",
        "message": "Cambio de pitcher confirmado. El juego continúa.",
    }


@router.post("/{game_id}/steal", summary="Intentar robo de base")
async def steal_base(
    game_id: str,
    payload: StealBaseRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Ejecuta un intento de robo de base (2B o 3B) por parte del equipo ofensivo.
    La probabilidad de éxito depende de los atributos del pitcher activo.
    Si el corredor es out, se registra el out, se evalúa cambio de entrada
    y se verifica la condición de fin de juego.
    """
    game = get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    if current_user_id not in (game.home_user_id, game.away_user_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta partida.")

    state = dict(game.state_data or {})
    active_pitcher_id = state.get("active_pitcher")

    pitcher_card = get_card_by_id(db, active_pitcher_id)
    pitcher_attrs = map_card_to_pitcher_attrs(pitcher_card) if pitcher_card else {"velocidad": 75, "control": 70, "movimiento": 70}

    # Lógica de dominio (incluye cambio de media entrada) en el engine
    success, description = steal_attempt(game, state, payload.target_base, pitcher_attrs)

    game.state_data = state

    db.commit()
    db.refresh(game)

    runners = state.get("runners", {})

    await manager.broadcast_to_game_view(game_id, lambda u: {
        "type": "STEAL_RESOLVED",
        "success": success,
        "description": description,
        "outs": game.outs,
        "runners": runners,
        "current_inning": game.current_inning,
        "is_top_inning": game.is_top_inning,
        "state_data": _player_state_for(game, u),
    })

    return {
        "status": "ok",
        "success": success,
        "description": description,
        "outs": game.outs,
        "runners": runners,
    }


