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
from app.engine.calculator import calculate_play_outcome
from app.engine.state_manager import process_at_bat_transition
from app.engine.fatigue_manager import apply_pitcher_fatigue, get_pitch_threshold, compute_fatigue_level
from app.engine.deck_manager import discard_used_tactic
from app.engine.tactical_actions import resolve_bunt, resolve_steal
from app.engine.tactic_resolver import accumulate_tactic_effects, new_default_tactic_modifiers
from app.engine.websocket_manager import manager
from app.engine.turn_guard import verify_player_turn
from app.engine.cpu_ai import (
    choose_pitch_from_repertoire,
    get_cpu_pitch_action,
    get_cpu_pitcher_change_decision,
    get_cpu_swing_action,
    is_cpu_turn,
)
from app.engine.attribute_mapper import map_card_to_pitcher_attrs, map_card_to_batter_attrs
from app.repositories import (
    count_user_inventory,
    find_pitchers_for_team,
    find_user_inventory_cards,
    find_user_inventory_pitchers,
    get_card_by_id,
    get_game_by_id,
    get_tactic_card_by_id,
)
from app.services.card_presenter import build_batter_payload, build_pitcher_payload

router = APIRouter(prefix="/api/v1/games", tags=["Motor de Jugabilidad 1v1"])


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _build_play_resolved_payload(game: GameSession, event: str, description: str, inning_completed: bool = False, user_id: str = None, db: Session = None) -> dict:
    """Construye el payload estándar de WebSocket para PLAY_RESOLVED."""
    state_with_role = dict(game.state_data or {})
    if user_id:
        state_with_role["user_role"] = "HOME" if user_id == game.home_user_id else "AWAY"
    
    # ⭐ Obtener estadísticas desde la BD
    pitcher_strikeouts = {}
    batter_stats = {}
    home_hits_total = 0
    away_hits_total = 0
    inning_runs = {}  # ⭐ NUEVO: {inning: {top: runs, bottom: runs}}
    
    if db:
        from app.engine.stats_recorder import get_game_box_score
        try:
            box_score = get_game_box_score(db, game.id)
            
            # Striker strikeouts
            if box_score and box_score.get("pitchers"):
                for pitcher_id, pitcher_stats in box_score["pitchers"].items():
                    pitcher_strikeouts[pitcher_id] = pitcher_stats.get("strikeouts", 0)
            
            # Batter stats (simplificado: solo los datos clave)
            if box_score and box_score.get("batters"):
                # Obtener lineups desde state_data (más confiable)
                home_lineup = state_with_role.get("home_lineup", [])
                away_lineup = state_with_role.get("away_lineup", [])
                
                home_lineup_ids = set(str(p) if isinstance(p, str) else str(p.get("id", "")) for p in home_lineup if p)
                away_lineup_ids = set(str(p) if isinstance(p, str) else str(p.get("id", "")) for p in away_lineup if p)
                
                print(f"⭐ [DEBUG HITS] home_lineup_ids({len(home_lineup_ids)}): {home_lineup_ids}")
                print(f"⭐ [DEBUG HITS] away_lineup_ids({len(away_lineup_ids)}): {away_lineup_ids}")
                
                for batter_id, bat_stats in box_score["batters"].items():
                    hits = bat_stats.get("hits", 0)
                    batter_id_str = str(batter_id)
                    
                    batter_stats[batter_id] = {
                        "at_bats": bat_stats.get("at_bats", 0),
                        "hits": hits,
                        "doubles": bat_stats.get("doubles", 0),
                        "triples": bat_stats.get("triples", 0),
                        "home_runs": bat_stats.get("home_runs", 0),
                        "rbi": bat_stats.get("rbi", 0),
                        "runs": bat_stats.get("runs", 0),
                        "strikeouts": bat_stats.get("strikeouts", 0),
                        "walks": bat_stats.get("walks", 0),
                    }
                    
                    # Acumular hits por equipo (comparar tanto el objeto como string)
                    if batter_id in home_lineup_ids or batter_id_str in home_lineup_ids:
                        home_hits_total += hits
                        print(f"⭐ [HITS] HOME batter {batter_id}: {hits} hits (total: {home_hits_total})")
                    elif batter_id in away_lineup_ids or batter_id_str in away_lineup_ids:
                        away_hits_total += hits
                        print(f"⭐ [HITS] AWAY batter {batter_id}: {hits} hits (total: {away_hits_total})")
                    else:
                        print(f"⭐ [HITS] UNMAPPED batter {batter_id} ({batter_id_str}): {hits} hits (not in either lineup)")
            
            # ⭐ NUEVO: Obtener carreras por inning de score_history
            # score_history se crea y actualiza en state_manager.py cuando se anotan carreras
            if db:
                score_history = state_with_role.get("score_history", {})
                print(f"⭐ [SCORE HISTORY] Carreras por inning: {score_history}")
                
                # Asegurar que todas las entradas están presentes (incluidas las sin carreras)
                inning_runs = {}
                for i in range(1, 10):  # Entradas 1-9
                    inning_runs[f"{i}_true"] = score_history.get(f"{i}_true", 0)
                    inning_runs[f"{i}_false"] = score_history.get(f"{i}_false", 0)
                
                print(f"⭐ [INNING RUNS] Desglose por entrada (from score_history): {inning_runs}")
                
        except Exception as e:
            print(f"⚠️ [STATS] Error obteniendo box score: {e}")
            import traceback
            traceback.print_exc()
    
    
    # ⭐ NUEVO: Obtener datos del pitcher y bateador activos para mostrar en la tarjeta
    active_pitcher_data = None
    active_batter_data = None
    
    if db:
        active_pitcher_id = state_with_role.get("active_pitcher")
        active_batter_id = state_with_role.get("active_batter")
        
        # Obtener datos del pitcher
        if active_pitcher_id:
            pitcher_card = get_card_by_id(db, active_pitcher_id)
            if pitcher_card:
                # ⭐ MEJORADO: Calcular pitch count y fatigue level con umbral dinámico por innings
                pitch_counts = state_with_role.get("pitch_counts", {})
                current_pitch_count = pitch_counts.get(active_pitcher_id, 0)

                # Obtener umbral dinámico basado en total_innings
                total_innings = state_with_role.get("total_innings", 9)
                pitch_threshold = get_pitch_threshold(total_innings)

                # Calcular fatigue level (0-100%) - usar la misma lógica que apply_pitcher_fatigue
                fatigue_level = compute_fatigue_level(current_pitch_count, total_innings)

                # ⭐ DEBUG: Logging de fatiga AGRESIVA (sin cap)
                print(f"🔍 [PITCHER STAMINA DEBUG - AGGRESSIVE]")
                print(f"   Pitcher ID: {active_pitcher_id}")
                print(f"   Current Pitch Count: {current_pitch_count}")
                print(f"   Total Innings: {total_innings}")
                print(f"   Dynamic Pitch Threshold: {pitch_threshold}")

                if current_pitch_count > pitch_threshold:
                    extra_pitches = current_pitch_count - pitch_threshold
                    penalty_factor = 1.0 - (0.10 * extra_pitches)
                    print(f"   ⚡ FATIGUE ACTIVATED!")
                    print(f"      Extra Pitches: {extra_pitches}")
                    print(f"      Penalty Factor (uncapped): {penalty_factor:.2f}")
                    print(f"      Degradation: {max(0, (1.0-penalty_factor)*100):.1f}%")
                else:
                    print(f"   ✅ No fatigue yet (under threshold)")

                print(f"   Final Fatigue Level (%): {fatigue_level:.2f}")
                print(f"   Status: {'🟢 FRESH' if fatigue_level < 40 else '🟡 MODERATE' if fatigue_level < 70 else '🟠 TIRED' if fatigue_level < 85 else '🔴 CRITICAL'}")

                active_pitcher_data = build_pitcher_payload(
                    pitcher_card,
                    with_stamina=True,
                    pitch_count=current_pitch_count,
                    fatigue_level=fatigue_level,
                )

        # Obtener datos del bateador
        if active_batter_id:
            batter_card = get_card_by_id(db, active_batter_id)
            if batter_card:
                active_batter_data = build_batter_payload(batter_card)
    
    # ⭐ DEBUG
    print(f"📊 [PLAY_RESOLVED PAYLOAD] event={event}, pitchers={len(pitcher_strikeouts)}, batters={len(batter_stats)}, home_hits={home_hits_total}, away_hits={away_hits_total}")
    print(f"📊 [FINAL SCORES] HOME={game.score_home}, AWAY={game.score_away}")
    
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
        "state_data": state_with_role,
        "inning_completed": inning_completed,
        "pitcher_strikeouts": pitcher_strikeouts,
        "batter_stats": batter_stats,  # ⭐ NUEVO
        "home_hits": home_hits_total,  # ⭐ NUEVO
        "away_hits": away_hits_total,  # ⭐ NUEVO
        "inning_runs": inning_runs,    # ⭐ NUEVO: {inning_is_top: runs}
        "active_pitcher": active_pitcher_data,  # ⭐ NUEVO: Datos del pitcher para la tarjeta
        "active_batter": active_batter_data,    # ⭐ NUEVO: Datos del bateador para la tarjeta
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
    mods = new_default_tactic_modifiers()

    if active_tactics.get("batter"):
        tac = get_tactic_card_by_id(db, active_tactics["batter"])
        if tac:
            mods = accumulate_tactic_effects(tac.effects, mods, is_pitcher_tactic=False)

    if active_tactics.get("pitcher"):
        tac = get_tactic_card_by_id(db, active_tactics["pitcher"])
        if tac:
            mods = accumulate_tactic_effects(tac.effects, mods, is_pitcher_tactic=True)

    return mods


async def _resolve_swing(
    game: GameSession,
    state: dict,
    swing_type: str,
    guessed_zone: int | None,
    guessed_pitch: str | None,
    db: Session,
    game_id: str,
    user_id: str = None,  # ⭐ NUEVO: para incluir user_role en el payload
) -> tuple[str, str, bool]:
    """
    Núcleo compartido entre execute_swing (humano) y la CPU en PvE.

    Ejecuta los pasos 1-6 del at-bat: fatiga, tácticas, cálculo, transición
    y broadcast WS. Persiste el estado y retorna (event, description, inning_ended).

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
    pitcher_card = get_card_by_id(db, active_pitcher_id)
    batter_card = get_card_by_id(db, active_batter_id)

    raw_pitcher_attrs = map_card_to_pitcher_attrs(pitcher_card) if pitcher_card else {"velocidad": 75, "control": 70, "movimiento": 70}
    batter_attrs = map_card_to_batter_attrs(batter_card) if batter_card else {"contacto": 70, "poder": 70, "vision": 70}
    
    # ⭐ MEJORADO: Pasar total_innings para ajustar dinámicamente el umbral de fatiga
    total_innings = state.get("total_innings", 9)
    pitcher_attrs = apply_pitcher_fatigue(raw_pitcher_attrs, current_count, total_innings)

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
    at_bat_ended, inning_ended, event, description = process_at_bat_transition(game, raw_event, state, db)

    # La descripción ya está completa desde state_manager.py
    # No la sobrescribimos, solo la usamos directamente

    # ⭐ NUEVO: Registrar evento en estadísticas
    if at_bat_ended:
        from app.engine.stats_recorder import record_game_event
        
        # ⭐ CORREGIDO: Usar el runs_scored ya calculado en state_manager
        # en lugar de recalcularlo (que daría valores incorrectos)
        runs_scored = state.get("last_runs_scored", 0)
        rbi = runs_scored
        
        print(f"📊 [RECORD EVENT] event={event}, runs_scored={runs_scored} (from state_manager)")
        
        try:
            record_game_event(
                db=db,
                game_id=game_id,
                event_type=event,
                inning=game.current_inning,
                is_top_inning=game.is_top_inning,
                batter_id=active_batter_id,
                pitcher_id=active_pitcher_id,
                balls=game.balls,
                strikes=game.strikes,
                outs=game.outs,
                runners_on_base=state.get("runners", {}),
                runs_scored=runs_scored,
                rbi=rbi,
            )
            print(f"✅ [STATS] Evento registrado: {event}")
        except Exception as e:
            print(f"❌ [STATS ERROR] {e}")

    # --- 7. Persistir y hacer broadcast ---
    state["current_pitch"] = None
    state["last_event"] = event
    game.state_data = state

    db.add(game)
    db.commit()
    db.refresh(game)

    # ⭐ ASEGURAR que los strikeouts están frescos de la BD antes de enviar por WebSocket
    payload = _build_play_resolved_payload(game, event, description, inning_completed=inning_ended, user_id=user_id, db=db)
    await manager.broadcast_to_game(game_id, payload)
    return event, description, inning_ended


async def _execute_cpu_pitcher_change(
    game: GameSession, state: dict, db: Session, game_id: str, difficulty: str
) -> bool:
    """
    Ejecuta un cambio de pitcher para la CPU si hay relevistas disponibles.
    
    Busca el pitcher del CPU (HOME o AWAY) en el inventario global,
    selecciona uno que no haya sido usado aún, y lo asigna como active_pitcher.
    
    Retorna: True si se ejecutó el cambio, False si no hay pitchers disponibles.
    """
    cpu_is_home = game.home_user_id == "CPU_BOT"
    cpu_is_away = game.away_user_id == "CPU_BOT"
    
    if not (cpu_is_home or cpu_is_away):
        return False  # No hay CPU en este juego
    
    active_pitcher_id = state.get("active_pitcher")
    pitch_counts: dict = state.get("pitch_counts", {})
    used_pitcher_ids = set(pitch_counts.keys())
    
    # Pitcher del CPU según su rol
    cpu_pitcher_field = "home_pitcher_id" if cpu_is_home else "away_pitcher_id"
    cpu_lineup_field = "home_lineup" if cpu_is_home else "away_lineup"
    cpu_user_id = game.home_user_id if cpu_is_home else game.away_user_id
    
    # Obtener el team_id del pitcher del CPU de referencia
    ref_pitcher_id = state.get(cpu_pitcher_field)
    if not ref_pitcher_id:
        print(f"🤖 [CPU PITCHER CHANGE] ❌ No reference pitcher found (field={cpu_pitcher_field})")
        return False
    
    ref_pitcher = get_card_by_id(db, ref_pitcher_id)
    if not ref_pitcher:
        print(f"🤖 [CPU PITCHER CHANGE] ❌ Reference pitcher not found in DB: {ref_pitcher_id}")
        return False
    
    cpu_team_id = ref_pitcher.team_id
    
    print(f"🤖 [CPU PITCHER CHANGE] Iniciando cambio de lanzador:")
    print(f"   - CPU Position: {'HOME' if cpu_is_home else 'AWAY'}")
    print(f"   - CPU Team ID: {cpu_team_id} | Team: {ref_pitcher.team.name if ref_pitcher.team else 'UNKNOWN'}")
    print(f"   - Current Pitcher: {ref_pitcher.name} (ID: {active_pitcher_id})")
    print(f"   - Already Used Pitchers: {used_pitcher_ids}")
    
    # Buscar pitchers disponibles en el equipo de la CPU (no usados, no el activo)
    available = find_pitchers_for_team(
        db,
        team_id=cpu_team_id,
        exclude_ids=used_pitcher_ids,
        excluded_id=active_pitcher_id,
    )
    
    print(f"   - Available Pitchers: {len(available)}")
    for pitcher in available:
        print(f"      ✓ {pitcher.name} (ID: {pitcher.id}) | Team: {pitcher.team.name if pitcher.team else 'UNKNOWN'} | OVR: {pitcher.overall} | Pos: {pitcher.position}")
    
    if not available:
        print(f"🤖 [CPU PITCHER CHANGE] ❌ No hay relevistas disponibles para el CPU")
        return False
    
    # Seleccionar al relevista con mayor OVR (mejor preparado)
    new_pitcher = max(available, key=lambda p: p.overall)
    print(f"🤖 [CPU PITCHER CHANGE] ✅ Seleccionado nuevo pitcher: {new_pitcher.name} (OVR {new_pitcher.overall})")
    print(f"   - Team: {new_pitcher.team.name if new_pitcher.team else 'UNKNOWN'} (ID: {new_pitcher.team_id})")
    print(f"   - Position: {new_pitcher.position} | Rarity: {new_pitcher.rarity}")
    
    # Ejecutar el cambio en state
    old_pitcher_id = state.get("active_pitcher")
    state["active_pitcher"] = new_pitcher.id
    
    # Actualizar home_pitcher_id / away_pitcher_id para que la próxima entrada lo use
    state[cpu_pitcher_field] = new_pitcher.id
    
    # Resetear contador de pitches para el nuevo pitcher
    pitch_counts[new_pitcher.id] = 0
    state["pitch_counts"] = pitch_counts
    
    game.state_data = state
    db.commit()
    db.refresh(game)
    
    print(f"🤖 [CPU PITCHER CHANGE] ✅ Cambio completado y guardado en BD")
    
    # ⭐ NUEVO: Obtener datos del pitcher anterior
    old_pitcher = None
    old_pitcher_data = None
    if old_pitcher_id:
        old_pitcher = get_card_by_id(db, old_pitcher_id)
        if old_pitcher:
            old_pitcher_data = build_pitcher_payload(old_pitcher, with_repertoire=True)
    
    # Construir datos del nuevo pitcher para broadcast
    new_pitcher_data = build_pitcher_payload(
        new_pitcher,
        with_repertoire=True,
        with_stamina=True,
        pitch_count=0,
        fatigue_level=0.0,
    )
    
    # Broadcast del cambio vía WebSocket
    await manager.broadcast_to_game(game_id, {
        "type": "PITCHER_CHANGED",
        "message": f"🔄 La CPU ha hecho un cambio de pitcher. Entra: {new_pitcher.name}",
        "old_pitcher_id": old_pitcher_id,
        "old_pitcher_data": old_pitcher_data,
        "new_pitcher_id": new_pitcher.id,
        "new_pitcher": new_pitcher_data,
        "state_data": game.state_data,
    })
    
    # ⭐ NUEVO: Marcar que se está esperando confirmación del usuario
    state["awaiting_pitcher_change_acknowledgment"] = True
    state["pending_pitcher_change"] = {
        "old_pitcher_id": old_pitcher_id,
        "new_pitcher_id": new_pitcher.id,
    }
    game.state_data = state
    db.commit()
    
    return True


async def trigger_cpu_response_if_needed(game: GameSession, state: dict, db: Session, game_id: str) -> None:
    """
    En partidas PvE, evalúa si le toca actuar a la CPU y ejecuta su acción.
    """
    if state.get("mode") != "PVE" or state.get("is_game_over"):
        print(f"🤖 [trigger_cpu] EARLY RETURN: mode={state.get('mode')}, is_game_over={state.get('is_game_over')}")
        return

    difficulty = state.get("difficulty", "MEDIUM")
    
    print(f"🤖 DEBUG trigger_cpu_response_if_needed:")
    print(f"   is_top_inning={game.is_top_inning}, home_user={game.home_user_id}, away_user={game.away_user_id}")
    cpu_pitcher_turn = is_cpu_turn(game, state, 'PITCHER')
    cpu_batter_turn = is_cpu_turn(game, state, 'BATTER')
    print(f"   cpu_turn_pitcher={cpu_pitcher_turn}, cpu_turn_batter={cpu_batter_turn}")
    print(f"   current_pitch={state.get('current_pitch')}")
    
    # Caso A: la CPU debe batear (hay un picheo humano pendiente)
    if cpu_batter_turn and state.get("current_pitch"):
        print(f"   ✅ CASO A: CPU debería batear")
        cpu_swing = get_cpu_swing_action(difficulty)

        _, _, _ = await _resolve_swing(
            game=game,
            state=state,
            swing_type=cpu_swing["swing_type"],
            guessed_zone=cpu_swing.get("guessed_zone"),
            guessed_pitch=cpu_swing.get("guessed_pitch"),
            db=db,
            game_id=game_id,
            user_id=None,  # CPU swing, sin user_id específico
        )
        # Tras el swing de la CPU puede haber cambiado la media entrada.
        state = dict(game.state_data or {})
        if state.get("is_game_over"):
            return

    # Caso B: la CPU debe pichear (no hay picheo pendiente y es el turno de la CPU)
    if cpu_pitcher_turn and not state.get("current_pitch"):
        print(f"   ✅ CASO B: CPU debería pichear")
        
        # ── NUEVO: Evaluar si la CPU debe cambiar pitcher ──────────────────
        active_pitcher_id = state.get("active_pitcher")
        if active_pitcher_id:
            pitch_count = state.get("pitch_counts", {}).get(active_pitcher_id, 0)
            pitcher_card = get_card_by_id(db, active_pitcher_id)
            
            if pitcher_card:
                # ← CORRECCIÓN: Calcular fatiga_level correctamente (no era None/0.0)
                total_innings = state.get("total_innings", 9)
                pitch_threshold = get_pitch_threshold(total_innings)
                fatigue_level = compute_fatigue_level(pitch_count, total_innings)
                
                print(f"🤖 [CPU FATIGUE CHECK] pitcher={active_pitcher_id}, pitch_count={pitch_count}, threshold={pitch_threshold}, fatigue={fatigue_level:.1f}%")
                
                # Decisión de la CPU: ¿cambiar pitcher?
                should_change = get_cpu_pitcher_change_decision(
                    pitch_count=pitch_count,
                    fatigue_level=fatigue_level,
                    difficulty=difficulty,
                )
                
                if should_change:
                    # Ejecutar el cambio de pitcher
                    changed = await _execute_cpu_pitcher_change(game, state, db, game_id, difficulty)
                    if changed:
                        # Recargar state después del cambio
                        state = dict(game.state_data or {})
                        active_pitcher_id = state.get("active_pitcher")
        
        # Usar solo pitch types del repertorio real de la carta del pitcher activo
        cpu_pitch = get_cpu_pitch_action(difficulty)

        if active_pitcher_id:
            pitcher_card = get_card_by_id(db, active_pitcher_id)
            pitch_type = choose_pitch_from_repertoire(pitcher_card.repertoire if pitcher_card else None)
            if pitch_type:
                cpu_pitch["pitch_type"] = pitch_type

        state["current_pitch"] = cpu_pitch
        game.state_data = state
        db.commit()
        db.refresh(game)  # ← ⭐ NUEVO: Recargar game después de commit para sincronizar
        print(f"   ✅ CPU picheo: {cpu_pitch['pitch_type']} a zona {cpu_pitch['zone']}")
        print(f"   ✅ State committed. current_pitch EN DB = {game.state_data.get('current_pitch')}")
        print(f"   ✅ Broadcasteando PITCH_COMMITTED al cliente...")

        await manager.broadcast_to_game(game_id, {
            "type": "PITCH_COMMITTED",
            "message": "La CPU ha seleccionado su picheo. Es tu turno de batear.",
            "has_pitched": True,
        })
    else:
        print(f"   ❌ CASO B no se ejecutó completamente")


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

    verify_player_turn(game, current_user_id, required_role="PITCHER")
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
    print(f"🎯 DEBUG swing: game_id={game_id}, user_id={current_user_id}")
    
    game = get_game_by_id(db, game_id)
    if not game:
        print(f"❌ ERROR: Juego no encontrado: {game_id}")
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    print(f"   home_user_id={game.home_user_id}, away_user_id={game.away_user_id}, is_top_inning={game.is_top_inning}")
    
    try:
        verify_player_turn(game, current_user_id, required_role="BATTER")
    except HTTPException as e:
        print(f"❌ TURN VERIFICATION FAILED: {e.detail}")
        raise

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
            await trigger_cpu_response_if_needed(game, state, db, game_id)
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
    event, description, inning_ended = await _resolve_swing(
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
        await trigger_cpu_response_if_needed(game, state, db, game_id)

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
    
    if not new_pitcher or new_pitcher.position not in ("SP", "RP", "TWP"):
        print(f"❌ Pitcher inválido o posición incorrecta")
        raise HTTPException(
            status_code=400,
            detail="La carta indicada no corresponde a un lanzador válido (SP, RP o TWP)."
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


