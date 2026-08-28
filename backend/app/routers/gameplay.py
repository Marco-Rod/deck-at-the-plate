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
from app.models import GameSession, PlayerCardModel, TacticCard, Team, GameEventLog
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
from app.engine.player_stats_formatter import format_player_stats

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
            pitcher_card = db.query(PlayerCardModel).filter(PlayerCardModel.id == active_pitcher_id).first()
            if pitcher_card:
                # ⭐ MEJORADO: Calcular pitch count y fatigue level con umbral dinámico por innings
                from app.engine.fatigue_manager import get_pitch_threshold
                
                pitch_counts = state_with_role.get("pitch_counts", {})
                current_pitch_count = pitch_counts.get(active_pitcher_id, 0)
                
                # Obtener umbral dinámico basado en total_innings
                total_innings = state_with_role.get("total_innings", 9)
                pitch_threshold = get_pitch_threshold(total_innings)
                
                # Calcular fatigue level (0-100%) - usar la misma lógica que apply_pitcher_fatigue
                FATIGUE_PENALTY_STEP = 15
                if current_pitch_count > pitch_threshold:
                    extra_pitches = current_pitch_count - pitch_threshold
                    # Penalty factor: 1.0 - (0.03 * (extra_pitches // FATIGUE_PENALTY_STEP + 1))
                    # Convertir a porcentaje de fatiga: (1 - penalty_factor) * 100
                    penalty_factor = 1.0 - (0.03 * (extra_pitches // FATIGUE_PENALTY_STEP + 1))
                    penalty_factor = max(0.5, penalty_factor)  # Límite: -50% máximo
                    fatigue_level = min(100, (1.0 - penalty_factor) * 100)  # ⭐ CORREGIDO: conversión a %
                else:
                    fatigue_level = 0.0
                
                # ⭐ DEBUG: Logging de fatiga
                print(f"🔍 [PITCHER STAMINA DEBUG]")
                print(f"   Pitcher ID: {active_pitcher_id}")
                print(f"   Current Pitch Count: {current_pitch_count}")
                print(f"   Total Innings: {total_innings}")
                print(f"   Dynamic Pitch Threshold: {pitch_threshold}")
                
                if current_pitch_count > pitch_threshold:
                    extra_pitches = current_pitch_count - pitch_threshold
                    penalty_factor = 1.0 - (0.03 * (extra_pitches // FATIGUE_PENALTY_STEP + 1))
                    penalty_factor = max(0.5, penalty_factor)
                    print(f"   ✅ FATIGUE ACTIVATED!")
                    print(f"      Extra Pitches: {extra_pitches}")
                    print(f"      Penalty Factor: {penalty_factor:.2f} ({(1.0-penalty_factor)*100:.1f}% degradation)")
                else:
                    print(f"   ✅ No fatigue yet")
                
                print(f"   Final Fatigue Level (%): {fatigue_level:.2f}")
                print(f"   Status: {'🟢 FRESH' if fatigue_level < 40 else '🟡 MODERATE' if fatigue_level < 70 else '🟠 TIRED' if fatigue_level < 85 else '🔴 CRITICAL'}")
                
                active_pitcher_data = {
                    "id": pitcher_card.id,
                    "name": pitcher_card.name,
                    "number": pitcher_card.number,
                    "overall": pitcher_card.overall,
                    "position": pitcher_card.position,
                    "rarity": pitcher_card.rarity.value if pitcher_card.rarity else "COMMON",
                    "team": pitcher_card.team.name if pitcher_card.team else "UNKNOWN",
                    "stats": format_player_stats(pitcher_card, "PITCHER"),
                    "role": "PITCHER",
                    "pitch_count": current_pitch_count,  # ⭐ Número de lanzamientos
                    "fatigue_level": fatigue_level,  # ⭐ Porcentaje de fatiga (0-100)
                }
        
        # Obtener datos del bateador
        if active_batter_id:
            batter_card = db.query(PlayerCardModel).filter(PlayerCardModel.id == active_batter_id).first()
            if batter_card:
                active_batter_data = {
                    "id": batter_card.id,
                    "name": batter_card.name,
                    "number": batter_card.number,
                    "overall": batter_card.overall,
                    "position": batter_card.position,
                    "rarity": batter_card.rarity.value if batter_card.rarity else "COMMON",
                    "team": batter_card.team.name if batter_card.team else "UNKNOWN",
                    "stats": format_player_stats(batter_card, "BATTER"),
                    "role": "BATTER",
                }
    
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
    pitcher_card = db.query(PlayerCardModel).filter(PlayerCardModel.id == active_pitcher_id).first() if active_pitcher_id else None
    batter_card = db.query(PlayerCardModel).filter(PlayerCardModel.id == active_batter_id).first() if active_batter_id else None

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
    at_bat_ended, inning_ended, event, description = process_at_bat_transition(game, raw_event, state)

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


def _is_cpu_turn(game: GameSession, state: dict, required_role: str) -> bool:
    """
    Determina si en este momento le toca actuar a la CPU.

    En modo PvE:
      - Si CPU es AWAY: Alta → CPU pichea, humano batea. Baja → humano pichea, CPU batea.
      - Si CPU es HOME: Alta → CPU pichea, humano batea. Baja → humano pichea, CPU batea.

    Args:
        required_role: 'PITCHER' o 'BATTER' — el rol que se está evaluando.
    """
    if state.get("mode") != "PVE":
        return False
    
    # ⭐ ARREGLADO: Identificar dónde está la CPU
    is_cpu_home = game.home_user_id == "CPU_BOT"
    is_cpu_away = game.away_user_id == "CPU_BOT"
    
    if not (is_cpu_home or is_cpu_away):
        return False  # No hay CPU en este juego

    if required_role == "PITCHER":
        # CPU pichea en la Alta si es local, o en la Baja si es visitante
        if is_cpu_home:
            return game.is_top_inning      # CPU local pichea en Alta
        else:
            return not game.is_top_inning  # CPU visitante pichea en Baja
    
    if required_role == "BATTER":
        # CPU batea en la Alta si es visitante, o en la Baja si es local
        if is_cpu_away:
            return game.is_top_inning      # CPU visitante batea en Alta
        else:
            return not game.is_top_inning  # CPU local batea en Baja

    return False


async def trigger_cpu_response_if_needed(game: GameSession, state: dict, db: Session, game_id: str) -> None:
    """
    En partidas PvE, evalúa si le toca actuar a la CPU y ejecuta su acción.
    """
    if state.get("mode") != "PVE" or state.get("is_game_over"):
        return

    difficulty = state.get("difficulty", "MEDIUM")
    
    print(f"🤖 DEBUG trigger_cpu_response_if_needed:")
    print(f"   is_top_inning={game.is_top_inning}, home_user={game.home_user_id}, away_user={game.away_user_id}")
    print(f"   cpu_turn_pitcher={_is_cpu_turn(game, state, 'PITCHER')}, cpu_turn_batter={_is_cpu_turn(game, state, 'BATTER')}")
    print(f"   current_pitch={bool(state.get('current_pitch'))}")

    # Caso A: la CPU debe batear (hay un picheo humano pendiente)
    if _is_cpu_turn(game, state, "BATTER") and state.get("current_pitch"):
        print(f"   ✅ CPU debería batear (Caso A)")
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
    if _is_cpu_turn(game, state, "PITCHER") and not state.get("current_pitch"):
        print(f"   ✅ CPU debería pichear (Caso B)")
        # Usar solo pitch types del repertorio real de la carta del pitcher activo
        active_pitcher_id = state.get("active_pitcher")
        cpu_pitch = get_cpu_pitch_action(difficulty)

        if active_pitcher_id:
            pitcher_card = db.query(PlayerCardModel).filter(
                PlayerCardModel.id == active_pitcher_id
            ).first()
            if pitcher_card and pitcher_card.repertoire:
                available_types = [p["pitch_type"] for p in pitcher_card.repertoire]
                if available_types:
                    import random as _random
                    cpu_pitch["pitch_type"] = _random.choice(available_types)

        state["current_pitch"] = cpu_pitch
        game.state_data = state
        db.commit()
        print(f"   ✅ CPU picheo: {cpu_pitch['pitch_type']} a zona {cpu_pitch['zone']}")

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
            # Validar que existe en repertorio
            pitch_stats = pitcher_card.get_pitch_stats(payload.pitch_type)
            if not pitch_stats:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El lanzador {pitcher_card.name} no tiene el picheo '{payload.pitch_type}' en su repertorio."
                )
            
            # ⭐ Validar que no exceda máximo de 4 pitcheos
            if not pitcher_card.validate_repertoire():
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
    
    game = db.query(GameSession).filter(GameSession.id == game_id).first()
    if not game:
        print(f"❌ ERROR: Juego no encontrado: {game_id}")
        raise HTTPException(status_code=404, detail="Sesión de juego no encontrada.")

    print(f"   home_user_id={game.home_user_id}, away_user_id={game.away_user_id}, is_top_inning={game.is_top_inning}")
    
    try:
        verify_player_turn(game, current_user_id, required_role="BATTER")
    except HTTPException as e:
        print(f"❌ TURN VERIFICATION FAILED: {e.detail}")
        raise

    state = dict(game.state_data or {})
    if not state.get("current_pitch"):
        print(f"❌ ERROR: No hay picheo previo en state")
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


