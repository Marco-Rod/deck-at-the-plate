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
from typing import Dict, Any

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
from app.core.enums import PITCHER_POSITIONS
from app.engine.deck_manager import discard_used_tactic
from app.engine.tactical_actions import resolve_steal
from app.engine.websocket_manager import manager
from app.engine.turn_guard import expected_actor, is_player_turn
from app.engine.attribute_mapper import map_card_to_pitcher_attrs
from app.engine.game_actions import resolve_swing, trigger_cpu_response
from app.repositories import (
    count_user_inventory,
    find_pitchers_for_team,
    find_user_inventory_cards,
    find_user_inventory_pitchers,
    get_card_by_id,
    get_game_by_id,
    get_tactic_card_by_id,
)
from app.services.card_presenter import build_pitcher_payload

router = APIRouter(prefix="/api/v1/games", tags=["Motor de Jugabilidad 1v1"])


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

    tactic = get_tactic_card_by_id(db, payload.tactic_id)
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
    # ⭐ DEBUG: Verificar que los datos llegan correctamente
    print(f"🎯 [DEBUG] Endpoint /pitch recibió:")
    print(f"   game_id: {game_id}")
    print(f"   payload.pitch_type: {payload.pitch_type}")
    print(f"   payload.zone: {payload.zone}")
    print(f"   current_user_id: {current_user_id}")
    
    game = get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    # ⭐ NUEVO: Validar que no haya cambio de pitcher pendiente
    state = dict(game.state_data or {})
    if state.get("awaiting_pitcher_change_acknowledgment"):
        print(f"🚫 [PITCH BLOCKED] Cambio de pitcher del rival pendiente de confirmación")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El rival cambió de pitcher. Debes confirmar el cambio antes de continuar.",
        )

    _require_turn(game, current_user_id, required_role="PITCHER")
    active_pitcher_id = state.get("active_pitcher")
    
    print(f"🎯 [DEBUG] active_pitcher_id: {active_pitcher_id}")
    
    if active_pitcher_id:
        pitcher_card = get_card_by_id(db, active_pitcher_id)
        print(f"🎯 [DEBUG] pitcher_card: {pitcher_card.name if pitcher_card else 'NOT FOUND'}")
        
        if pitcher_card and payload.pitch_type != "IBB":
            # Validar que existe en repertorio
            pitch_stats = pitcher_card.get_pitch_stats(payload.pitch_type)
            print(f"🎯 [DEBUG] pitch_stats para '{payload.pitch_type}': {pitch_stats}")
            
            if not pitch_stats:
                print(f"❌ [ERROR] El lanzador {pitcher_card.name} no tiene '{payload.pitch_type}' en repertorio")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El lanzador {pitcher_card.name} no tiene el picheo '{payload.pitch_type}' en su repertorio."
                )
            
            # ⭐ Validar que no exceda máximo de 4 pitcheos
            if not pitcher_card.validate_repertoire():
                print(f"❌ [ERROR] Repertorio inválido para {pitcher_card.name}")
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
    print(f"✅ [DEBUG] State guardado con pitch: {state['current_pitch']}")

    await manager.broadcast_to_game(game_id, {
        "type": "PITCH_COMMITTED",
        "message": "El lanzador ha ejecutado su picheo. Esperando swing del bateador.",
        "has_pitched": True,
    })

    # En PvE: si la CPU es la bateadora en este momento, ejecuta su swing ahora.
    state = dict(game.state_data or {})
    if not state.get("is_game_over"):
        await trigger_cpu_response(game, state, db, game_id)

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
    print(f"🎯 DEBUG swing: game_id={game_id}, user_id={current_user_id}")
    
    game = get_game_by_id(db, game_id)
    if not game:
        print(f"❌ ERROR: Juego no encontrado: {game_id}")
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    print(f"   home_user_id={game.home_user_id}, away_user_id={game.away_user_id}, is_top_inning={game.is_top_inning}")
    
    _require_turn(game, current_user_id, required_role="BATTER")

    # ⭐ NUEVO: Expulsar todas las sesiones cacheadas y obtener una fresca de la BD
    db.expunge_all()
    game = get_game_by_id(db, game_id)
    db.refresh(game)
    state = dict(game.state_data or {})
    
    # ⭐ NUEVO: Validar que no haya cambio de pitcher pendiente
    if state.get("awaiting_pitcher_change_acknowledgment"):
        print(f"🚫 [SWING BLOCKED] Cambio de pitcher del rival pendiente de confirmación")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El rival cambió de pitcher. Debes confirmar el cambio antes de continuar.",
        )
    
    current_pitch = state.get("current_pitch")
    
    # ⭐ CRÍTICO: Si no hay picheo y debería haber CPU pitcher, ejecutar CPU response aquí
    if not current_pitch:
        print(f"   ⚠️ No hay pitch. Verificando si CPU debería haber lanzado...")
        
        if is_cpu_turn(game, state, "PITCHER"):
            print(f"   🤖 CPU debería haber lanzado! Ejecutando trigger ahora...")
            await trigger_cpu_response(game, state, db, game_id)
            # Recargar state después de que CPU lance
            db.expunge_all()
            game = get_game_by_id(db, game_id)
            db.refresh(game)
            state = dict(game.state_data or {})
            current_pitch = state.get("current_pitch")
            print(f"   ✅ Después de trigger, current_pitch = {bool(current_pitch)}")
    
    if not current_pitch:
        print(f"❌ ERROR: No hay picheo previo en state")
        print(f"   State keys: {list(state.keys())}")
        print(f"   is_top_inning: {game.is_top_inning}")
        print(f"   active_pitcher_id: {state.get('active_pitcher')}")
        print(f"   Game mode: {state.get('mode')}")
        raise HTTPException(status_code=400, detail="El lanzador aún no ha realizado su picheo para este turno.")

    print(f"   ✅ Swing válido, resolviendo jugada...")
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
    print(f"🔍 [CHANGE_PITCHER] Request recibido")
    print(f"🔍 game_id: {game_id}")
    print(f"🔍 new_pitcher_id: {payload.new_pitcher_id}")

    game = get_game_by_id(db, game_id)
    if not game:
        print(f"❌ Juego NO encontrado: {game_id}")
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    # Solo usuarios involucrados en la partida pueden hacer cambios.
    if current_user_id not in (game.home_user_id, game.away_user_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta partida.")

    active_state_pre = dict(game.state_data or {})
    new_pitcher = get_card_by_id(db, payload.new_pitcher_id)
    old_pitcher = get_card_by_id(db, active_state_pre.get("active_pitcher"))
    
    print(f"🔍 Pitcher anterior: {old_pitcher.name if old_pitcher else 'UNKNOWN'} ({old_pitcher.id if old_pitcher else 'N/A'})")
    print(f"🔍 Pitcher nuevo: {new_pitcher.name if new_pitcher else 'UNKNOWN'} ({payload.new_pitcher_id})")
    
    if not new_pitcher or new_pitcher.position not in PITCHER_POSITIONS:
        print(f"❌ Pitcher inválido o posición incorrecta")
        raise HTTPException(
            status_code=400,
            detail="La carta indicada no corresponde a un lanzador válido (SP, RP, CP o TWP)."
        )

    state = dict(game.state_data or {})

    # ── Validar mínimo de lanzamientos antes de permitir el cambio ──────────
    MIN_PITCHES_TO_CHANGE = 5
    active_pitcher_id = state.get("active_pitcher")
    pitch_counts_check: dict = state.get("pitch_counts", {})
    current_pitch_count = pitch_counts_check.get(active_pitcher_id, 0) if active_pitcher_id else 0

    if current_pitch_count < MIN_PITCHES_TO_CHANGE:
        raise HTTPException(
            status_code=400,
            detail=f"El lanzador debe haber lanzado al menos {MIN_PITCHES_TO_CHANGE} pitches. Lleva {current_pitch_count}."
        )

    old_pitcher_id = state.get("active_pitcher")
    state["active_pitcher"] = payload.new_pitcher_id

    # ── Actualizar home_pitcher_id / away_pitcher_id según quién es el usuario ──
    # state_manager usa estos campos para restaurar el pitcher al cambiar de media entrada.
    # Si no se actualizan aquí, el inning siguiente restaura el pitcher original.
    is_home_user = (current_user_id == game.home_user_id)
    if is_home_user:
        state["home_pitcher_id"] = payload.new_pitcher_id
    else:
        state["away_pitcher_id"] = payload.new_pitcher_id

    print(f"🔄 [CHANGE_PITCHER] Cambiando {'HOME' if is_home_user else 'AWAY'} pitcher")
    print(f"   {old_pitcher.name if old_pitcher else 'OLD PITCHER'} ({old_pitcher_id}) → {new_pitcher.name} ({payload.new_pitcher_id})")

    pitch_counts = state.get("pitch_counts", {})
    pitch_counts[payload.new_pitcher_id] = 0  # Reset pitch count para el nuevo pitcher
    state["pitch_counts"] = pitch_counts
    
    # Log remaining available pitchers
    print(f"\n📊 [PITCHERS REMAINING AFTER CHANGE]")
    remaining_pitchers = find_pitchers_for_team(
        db,
        team_id=new_pitcher.team_id,
        exclude_ids={payload.new_pitcher_id},
    )
    print(f"   Available backups: {len(remaining_pitchers)}")
    for p in remaining_pitchers[:5]:
        print(f"      - {p.name} ({p.id}) | OVR: {p.overall}")
    print()

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

    print(f"✅ [PITCHER CHANGE] {old_pitcher_id} → {payload.new_pitcher_id} ({new_pitcher.name})")

    # ⭐ NUEVO: Broadcast del cambio vía WebSocket
    await manager.broadcast_to_game(game_id, {
        "type": "PITCHER_CHANGED",
        "message": f"🔄 Cambio de picher. Entra a la loma: {new_pitcher.name}",
        "old_pitcher_id": old_pitcher_id,
        "new_pitcher_id": payload.new_pitcher_id,
        "new_pitcher": new_pitcher_data,
        "state_data": game.state_data,
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
    print(f"🔍 [GET_RIVAL_AVAILABLE_PITCHERS] game_id={game_id}")

    game = get_game_by_id(db, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    if current_user_id not in (game.home_user_id, game.away_user_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esta partida.")

    state = dict(game.state_data or {})
    active_pitcher_id = state.get("active_pitcher")
    
    # Determinar el team_id del rival (CPU)
    # El rival es el que NO es el usuario
    user_role = state.get("user_role")  # 'HOME' o 'AWAY'
    
    if user_role == "HOME":
        # Usuario es HOME, rival es AWAY
        rival_pitcher_id = state.get("away_pitcher_id")
    else:
        # Usuario es AWAY, rival es HOME
        rival_pitcher_id = state.get("home_pitcher_id")
    
    # Obtener el pitcher actual del rival para extraer su team_id
    ref_pitcher = get_card_by_id(db, rival_pitcher_id)
    if not ref_pitcher or not ref_pitcher.team_id:
        print(f"❌ No rival pitcher found or team_id missing: {rival_pitcher_id}")
        return {
            "status": "error",
            "count": 0,
            "available_pitchers": [],
            "message": "No se pudo determinar el equipo rival"
        }
    
    rival_team_id = ref_pitcher.team_id
    print(f"🔍 Rival team_id: {rival_team_id}, active_pitcher={active_pitcher_id}")

    # ── Buscar todos los pitchers del equipo rival ──────────────────────────
    rival_pitchers = find_pitchers_for_team(
        db,
        team_id=rival_team_id,
        excluded_id=active_pitcher_id,
    )

    print(f"🔍 Total pitchers del equipo rival: {len(rival_pitchers)}")
    for p in rival_pitchers[:10]:
        print(f"   - {p.name} ({p.id}) | Pos: {p.position} | OVR: {p.overall}")

    # ── Pitchers que ya lanzaron en este partido ────────────────────────────
    pitch_counts: dict = state.get("pitch_counts", {})
    used_pitcher_ids = set(pitch_counts.keys())

    print(f"🔍 Pitchers ya usados en el partido: {len(used_pitcher_ids)}")
    if used_pitcher_ids:
        for pid in list(used_pitcher_ids)[:5]:
            used_pitcher = get_card_by_id(db, pid)
            if used_pitcher:
                print(f"   - {used_pitcher.name} ({pid}) | Pitches: {pitch_counts[pid]}")

    available_pitchers = [
        build_pitcher_payload(card, already_used=card.id in used_pitcher_ids)
        for card in rival_pitchers
    ]

    print(f"✅ [RIVAL AVAILABLE PITCHERS] {len(available_pitchers)} disponibles (excluido active={active_pitcher_id})")
    for p in available_pitchers[:5]:
        print(f"   ✓ {p['name']} ({p['id']}) | Already Used: {p['already_used']}")

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
    print(f"\n🔍 [GET_AVAILABLE_PITCHERS] game_id={game_id}, user_id={current_user_id}")

    game = get_game_by_id(db, game_id)
    if not game:
        print(f"❌ Game not found: {game_id}")
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    # ── Validar que el user del token corresponde a un jugador humano del juego ────
    if current_user_id not in (game.home_user_id, game.away_user_id):
        print(f"❌ User {current_user_id} not in game. home={game.home_user_id}, away={game.away_user_id}")
        raise HTTPException(status_code=403, detail="El usuario no pertenece a este juego.")

    if current_user_id == "CPU_BOT":
        print(f"❌ CPU_BOT cannot change pitcher")
        raise HTTPException(status_code=400, detail="El CPU no puede cambiar pitcher manualmente.")

    user_id = current_user_id
    state = dict(game.state_data or {})
    active_pitcher_id = state.get("active_pitcher")

    print(f"📋 Game info:")
    print(f"   home_user_id={game.home_user_id}")
    print(f"   away_user_id={game.away_user_id}")
    print(f"   active_pitcher_id={active_pitcher_id}")

    # ── DEBUG: Contar total de cards en UserCardInventory del usuario ────
    total_inventory = count_user_inventory(db, user_id)
    print(f"\n📦 [INVENTORY DEBUG]")
    print(f"   Total cards en inventario del usuario: {total_inventory}")

    # ── DEBUG: Mostrar primeras 10 cartas del usuario ────
    all_user_cards = find_user_inventory_cards(db, user_id, limit=10)
    print(f"   Primeras 10 cartas del usuario:")
    for inv_card in all_user_cards:
        card = get_card_by_id(db, inv_card.card_id)
        if card:
            print(f"      - {card.name} ({card.id}) | Pos: {card.position}")

    # ── Buscar pitchers en el inventario del usuario ─────────────────────────
    inventory_pitchers = find_user_inventory_pitchers(
        db,
        user_id=user_id,
        excluded_id=active_pitcher_id,
    )

    print(f"\n🎯 [PITCHERS QUERY]")
    print(f"   Pitchers encontrados en inventario: {len(inventory_pitchers)}")
    for p in inventory_pitchers[:15]:
        print(f"      - {p.name} ({p.id}) | Pos: {p.position} | OVR: {p.overall}")

    # ── Pitchers que ya lanzaron en este partido ────────────────────────────
    pitch_counts: dict = state.get("pitch_counts", {})
    used_pitcher_ids = set(pitch_counts.keys())

    print(f"\n📊 [PITCH HISTORY]")
    print(f"   Pitchers ya usados en el partido: {len(used_pitcher_ids)}")
    if used_pitcher_ids:
        for pid in list(used_pitcher_ids)[:10]:
            used_pitcher = get_card_by_id(db, pid)
            if used_pitcher:
                print(f"      - {used_pitcher.name} ({pid}) | Pitches: {pitch_counts[pid]}")

    available_pitchers = [
        build_pitcher_payload(card, already_used=card.id in used_pitcher_ids)
        for card in inventory_pitchers
    ]

    print(f"\n✅ [RESULT]")
    print(f"   Total disponibles: {len(available_pitchers)}")
    for p in available_pitchers[:10]:
        print(f"      ✓ {p['name']} ({p['id']}) | OVR: {p['overall']} | Already Used: {p['already_used']}")
    print()

    return {
        "status": "ok",
        "count": len(available_pitchers),
        "available_pitchers": available_pitchers,
    }


@router.post("/{game_id}/acknowledge-pitcher-change", summary="Confirmar cambio de pitcher del rival")
def acknowledge_pitcher_change(
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
    
    if not state.get("awaiting_pitcher_change_acknowledgment"):
        print(f"⚠️  [ACK PITCHER CHANGE] No hay cambio pendiente para confirmar")
        return {
            "status": "ok",
            "message": "No hay cambio de pitcher pendiente",
        }
    
    print(f"✅ [ACK PITCHER CHANGE] Usuario confirmó cambio de pitcher")
    print(f"   old_pitcher: {state.get('pending_pitcher_change', {}).get('old_pitcher_id')}")
    print(f"   new_pitcher: {state.get('pending_pitcher_change', {}).get('new_pitcher_id')}")
    
    # Limpiar los flags de bloqueo
    state["awaiting_pitcher_change_acknowledgment"] = False
    state["pending_pitcher_change"] = None
    
    game.state_data = state
    db.commit()
    db.refresh(game)
    
    # Broadcast para notificar que se desbloqueó
    import asyncio
    import logging
    from app.engine.websocket_manager import manager
    try:
        asyncio.run(manager.broadcast_to_game(game_id, {
            "type": "PITCHER_CHANGE_ACKNOWLEDGED",
            "message": "El juego continúa. El nuevo pitcher está listo.",
            "state_data": game.state_data,
        }))
    except Exception as e:  # noqa: BLE001 - el broadcast no debe romper el flujo
        logging.getLogger(__name__).warning(
            "No se pudo emitir el broadcast de ack de cambio de pitcher: %s", e
        )
    
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


