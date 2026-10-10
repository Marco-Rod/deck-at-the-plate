"""
Acciones del at-bat (motor)
===========================
Capa de servicio del engine: concentra la lógica compartida que antes vivía en
el router `gameplay.py` y que NO es responsabilidad de HTTP:

  - ``build_play_resolved_payload`` : payload estándar del broadcast PLAY_RESOLVED.
  - ``apply_tactic_modifiers``       : acumula modificadores de cartas tácticas activas.
  - ``resolve_swing``                : núcleo 1-7 del at-bat (fatiga, cálculo, transición,
                                       estadísticas, telemetría pitch-by-pitch y broadcast WS).
  - ``execute_cpu_pitcher_change``   : cambio de lanzador decidido por la CPU.
  - ``trigger_cpu_response``         : orquesta la respuesta CPU tras una acción humana (PvE).

Beneficios SOLID:
    - SRP: el router queda con la capa HTTP (auth, HTTPException, schemas) y este
      módulo con las reglas de juego y la emisión WS.
    - Elimina la dependencia indirecta del motor con FastAPI (aquí no se importa
      `fastapi` en ningún punto).
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Callable, Literal

from app.core.enums import BatterApproach, SwingType
from app.engine.attribute_mapper import (
    map_card_to_batter_attrs,
    map_card_to_pitcher_attrs,
)
from app.engine.build import ENGINE_BUILD
from app.engine.calculator import calculate_play_outcome_with_trace
from app.engine.cpu_ai import (
    choose_pitch_from_repertoire,
    get_cpu_pitch_action,
    get_cpu_pitcher_change_decision,
    get_cpu_swing_action,
    is_cpu_turn,
)
from app.engine.fatigue_manager import (
    apply_pitcher_fatigue,
    compute_fatigue_level,
    get_fatigue_band,
    get_fatigue_factor,
    get_pitch_threshold,
    get_workload,
)
from app.engine.state_manager import process_at_bat_transition
from app.engine.stuff_policy import STUFF_BASELINE
from app.engine.tactic_resolver import (
    accumulate_tactic_effects,
    new_default_tactic_modifiers,
)
from app.engine.tactical_actions import resolve_bunt
from app.engine.bullpen import perform_pitcher_change
from app.engine.websocket_manager import manager
from app.engine.fog_of_war import sanitize_state_for_player
from app.models import GameSession
from app.repositories import (
    get_card_by_id,
    get_game_box_score,
    get_tactic_card_by_id,
    record_game_event,
)
from app.repositories.pitch_telemetry_repository import record_pitch_event
from app.services.card_presenter import build_batter_payload, build_pitcher_payload
from app.services.pitch_telemetry import (
    build_pitch_event_log_payload,
    pitch_family_for_runtime,
)

logger = logging.getLogger(__name__)


@dataclass
class PendingBroadcast:
    """Efecto WebSocket diferido hasta que la unidad de trabajo sea durable."""

    channel: Literal["to_game", "to_game_view"]
    game_id: str
    payload: dict | Callable[[str], dict | None]


async def publish_pending_broadcasts(events: list[PendingBroadcast]) -> None:
    """Publica eventos diferidos en el mismo orden en que fueron generados."""
    for event in events:
        if event.channel == "to_game":
            await manager.broadcast_to_game(event.game_id, event.payload)
        else:
            await manager.broadcast_to_game_view(event.game_id, event.payload)


async def _publish_or_defer(
    event: PendingBroadcast,
    pending_broadcasts: list[PendingBroadcast] | None,
) -> None:
    if pending_broadcasts is None:
        await publish_pending_broadcasts([event])
    else:
        pending_broadcasts.append(event)


def build_play_resolved_payload(game: GameSession, event: str, description: str, inning_completed: bool = False, user_id: str = None, db=None) -> dict:
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
                    elif batter_id in away_lineup_ids or batter_id_str in away_lineup_ids:
                        away_hits_total += hits
            
            # ⭐ NUEVO: Obtener carreras por inning de score_history
            # score_history se crea y actualiza en state_manager.py cuando se anotan carreras
            score_history = state_with_role.get("score_history", {})
            total_innings = int(state_with_role.get("total_innings", 9))

            # Asegurar que todas las entradas están presentes (incluidas las sin carreras)
            inning_runs = {}
            for i in range(1, total_innings + 1):  # Entradas 1..total_innings
                inning_runs[f"{i}_true"] = score_history.get(f"{i}_true", 0)
                inning_runs[f"{i}_false"] = score_history.get(f"{i}_false", 0)

        except Exception as e:
            logger.warning("Error obteniendo box score: %s", e)
    
    
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
                # ⭐ MEJORADO: Calcular pitch count y fatiga con umbral dinámico por innings
                pitch_counts = state_with_role.get("pitch_counts", {})
                current_pitch_count = pitch_counts.get(active_pitcher_id, 0)

                total_innings = state_with_role.get("total_innings", 9)
                pitch_threshold = get_pitch_threshold(total_innings)
                fatigue_factor = get_fatigue_factor(current_pitch_count, pitch_threshold)
                fatigue_band = get_fatigue_band(fatigue_factor)
                # fatigue_level legacy: se mantiene por compatibilidad (deprecado)
                fatigue_level = compute_fatigue_level(current_pitch_count, total_innings)

                active_pitcher_data = build_pitcher_payload(
                    pitcher_card,
                    with_stamina=True,
                    pitch_count=current_pitch_count,
                    fatigue_level=fatigue_level,
                    fatigue_factor=fatigue_factor,
                    fatigue_band=fatigue_band.value,
                )

        # Obtener datos del bateador
        if active_batter_id:
            batter_card = get_card_by_id(db, active_batter_id)
            if batter_card:
                active_batter_data = build_batter_payload(batter_card)
    
    payload = {
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
    return payload


def _fatigue_factor(base_attr: int, fatigued_attr: int) -> float:
    """Factor de degradación (0..1) de un atributo provocado por la fatiga.

    El factor es ``fatigado / base``: la identidad del lanzamiento (repertorio)
    se multiplica por este factor para obtener su valor efectivo. Cuando el
    atributo base es 0/negativo (dominio degenerado) el factor es identidad,
    evitando división por cero sin cambiar el resultado del juego.
    """
    if base_attr <= 0:
        return 1.0
    return fatigued_attr / base_attr


def apply_tactic_modifiers(active_tactics: dict, db) -> dict:
    """
    Lee las cartas tácticas activas desde la DB y acumula sus modificadores.
    Retorna un dict listo para pasar al motor (calculate_play_outcome[_with_trace]).
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


def _event_value(event) -> str:
    """Normaliza un evento (miembro de ``Event`` o string) a su valor canónico."""
    return event.value if hasattr(event, "value") else str(event)


def _record_pitch_telemetry(
    db,
    *,
    game_id: str,
    plate_appearance_id: str,
    pitch_number: int,
    batter_card,
    pitcher_card,
    swing_type: str,
    guessed_zone: int | None,
    current_pitch: dict,
    balls_before: int,
    strikes_before: int,
    outs_before: int,
    pitcher_fatigue: float,
    tactic_modifiers: dict | None,
    trace: dict,
    result: str,
) -> None:
    """Persiste el PitchEventLog del pitch RECIÉN resuelto (P5-A).

    Honestidad: el log se construye sólo con datos que el engine ya conocía al
    resolver (la distribución y el rng vienen del trace del motor). Nada se
    fabrica. La escritura es POST-resolución y falla ruidosamente si el builder
    rechaza el payload: el commit lo hace el caller y la transacción revierte
    completa (misma política que GameEventLog).

    Normalizaciones de dominio del Matchup Engine V1:
      - TAKE nunca lleva ``batter_zone_choice`` ni ``zone_match``: la zona la
        impone el pitch. Un ``guessed_zone`` que la CPU aprecie durante un TAKE
        es un artefacto del engine legado que V1 reemplaza; no sobrevive al log.
      - NORMAL/POWER/BUNT → approach REACT (no hay apuesta a familia de
        lanzamiento que acertar); TAKE → approach TAKE. ``approach_match`` es
        NULL en ambos (no existe acierto binario, definición del modelo).
    """
    if not batter_card or not pitcher_card:
        # Las FKs de pitch_event_logs exigen tarjetas reales. Sin ellas no hay
        # duelo registrable; mejor omisión explícita que un id inventado.
        logger.warning(
            "PitchEventLog omitido (%s): faltan tarjetas (batter=%s, pitcher=%s)",
            game_id, bool(batter_card), bool(pitcher_card),
        )
        return

    is_take = swing_type == SwingType.TAKE
    if is_take:
        batter_approach = BatterApproach.TAKE
        batter_zone_choice = None
        zone_match = False
    else:
        batter_approach = BatterApproach.REACT
        batter_zone_choice = guessed_zone
        zone_match = (guessed_zone == current_pitch.get("zone"))

    # matchup_inputs = atributos EFECTIVOS que el engine usó (trace del motor).
    matchup_inputs = None
    if trace.get("matchup_inputs"):
        matchup_inputs = {
            key: trace["matchup_inputs"][key]
            for key in ("contact", "power", "vision", "velocity", "control", "movement", "stuff")
        }

    pitch_type = _event_value(current_pitch.get("pitch_type", "4-SEAM"))

    payload = build_pitch_event_log_payload(
        game_id=game_id,
        plate_appearance_id=plate_appearance_id,
        pitch_number=pitch_number,
        batter_card_id=batter_card.id,
        pitcher_card_id=pitcher_card.id,
        batter_player_id=getattr(batter_card, "player_id", None),
        pitcher_player_id=getattr(pitcher_card, "player_id", None),
        batter_approach=batter_approach,
        pitcher_zone_choice=current_pitch.get("zone"),
        pitch_type=pitch_type,
        pitch_family=pitch_family_for_runtime(pitch_type),
        probability_distribution=trace.get("distribution"),
        rng_value=trace.get("rng_value"),
        result=result,
        engine_version=ENGINE_BUILD,
        batter_zone_choice=batter_zone_choice,
        zone_match=zone_match,
        balls_before=balls_before,
        strikes_before=strikes_before,
        outs_before=outs_before,
        pitcher_fatigue=pitcher_fatigue,
        tactical_modifiers=tactic_modifiers,
        matchup_inputs=matchup_inputs,
    )
    record_pitch_event(db, payload)


async def resolve_swing(
    game: GameSession,
    state: dict,
    swing_type: str,
    guessed_zone: int | None,
    guessed_pitch: str | None,
    db,
    game_id: str,
    user_id: str = None,  # ⭐ NUEVO: para incluir user_role en el payload
    pending_broadcasts: list[PendingBroadcast] | None = None,
) -> tuple[str, str, bool]:
    """
    Núcleo compartido entre execute_swing (humano) y la CPU en PvE.

    Ejecuta los pasos del at-bat y difiere el broadcast cuando recibe una cola
    transaccional. Retorna (event, description, inning_ended).

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

    # --- 0. Telemetría P5-A: contexto PRE-pitch (el conteo aún no cambió) ---
    # El log del pitch captura el conteo tal y como el bateador lo veía al
    # enfrentar este envío. game.balls/strikes/outs se mutan en la transición
    # (paso 6), así que se congelan aquí.
    balls_before = game.balls
    strikes_before = game.strikes
    outs_before = game.outs

    # Identidad de plate-appearance: estable DENTRO del mismo PA (la guarda
    # state_data entre pitches) y nueva por PA (se reinicia al terminar). Se
    # usa para agrupar pitch_event_logs y sellar el event terminal.
    plate_appearance_id = state.get("plate_appearance_id")
    if not plate_appearance_id:
        plate_appearance_id = f"pa_{uuid.uuid4().hex[:12]}"
        state["plate_appearance_id"] = plate_appearance_id
        state["pa_pitch_number"] = 0
    pa_pitch_number = state.get("pa_pitch_number", 0) + 1
    state["pa_pitch_number"] = pa_pitch_number

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

    raw_pitcher_attrs = map_card_to_pitcher_attrs(pitcher_card) if pitcher_card else {"velocidad": 75, "control": 70, "movimiento": 70, "stuff": STUFF_BASELINE}
    batter_attrs = map_card_to_batter_attrs(batter_card) if batter_card else {"contacto": 70, "poder": 70, "vision": 70}
    
    # ⭐ MEJORADO: Pasar total_innings para ajustar dinámicamente el umbral de fatiga
    total_innings = state.get("total_innings", 9)
    pitcher_attrs = apply_pitcher_fatigue(raw_pitcher_attrs, current_count, total_innings)

    # --- NUEVO: Extraer estadísticas específicas del picheo lanzado desde el repertorio ---
    selected_pitch_type = current_pitch.get("pitch_type", "4-SEAM")
    pitch_specific_stats = pitcher_card.get_pitch_stats(selected_pitch_type) if pitcher_card else None


    if pitch_specific_stats:
        # La fatiga fue calculada sobre los atributos globales; derivamos el
        # factor de degradación para aplicarlo al atributo específico del
        # lanzamiento sin perder la identidad del repertorio:
        #     identity del lanzamiento × estado físico del pitcher
        velocity_factor = _fatigue_factor(
            raw_pitcher_attrs["velocidad"], pitcher_attrs["velocidad"]
        )
        control_factor = _fatigue_factor(
            raw_pitcher_attrs["control"], pitcher_attrs["control"]
        )
        movement_factor = _fatigue_factor(
            raw_pitcher_attrs["movimiento"], pitcher_attrs["movimiento"]
        )

        # Enriquecemos current_pitch con los datos reales del repertorio para
        # calculator.py, degradados por fatiga. Redondeo int, igual criterio
        # que apply_pitcher_fatigue (el calculator opera con enteros).
        current_pitch["velocity"] = int(
            pitch_specific_stats.get("velocity", raw_pitcher_attrs["velocidad"])
            * velocity_factor
        )
        current_pitch["control"] = int(
            pitch_specific_stats.get("control", raw_pitcher_attrs["control"])
            * control_factor
        )
        current_pitch["movement"] = int(
            pitch_specific_stats.get("movement", raw_pitcher_attrs["movimiento"])
            * movement_factor
        )
    active_tactics = state.get("active_tactics", {})

    # --- 3. Procesamiento especial de BUNT (trace aditivo en el resolver) ---
    trace: dict = {}
    if swing_type == "BUNT":
        raw_event, description, sac_success = resolve_bunt(
            pitcher_attrs, batter_attrs, state.get("runners", {}), _trace=trace,
        )
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
        tactics_modifiers = apply_tactic_modifiers(active_tactics, db)

        # --- 5. Calcular resultado (con trace, misma resolución bit-exacta) ---
        traced_play = calculate_play_outcome_with_trace(
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
        raw_event, description = traced_play.result
        trace = traced_play.trace

    # --- 6. Transición de estado ---
    at_bat_ended, inning_ended, event, description = process_at_bat_transition(game, raw_event, state)

    # --- 6.5 Telemetría pitch-by-pitch (P5-A) ---
    # El log se escribe DESPUÉS de cerrar la resolución del pitch (regla del
    # modelo: nunca se registran secretos del rival antes de resolver). Los
    # datos provienen del trace del engine: distribución final ex-ante y el
    # draw determinante, sin inventar nada.
    fatigue_factor = get_fatigue_factor(current_count, get_pitch_threshold(total_innings))
    _record_pitch_telemetry(
        db=db,
        game_id=game_id,
        plate_appearance_id=plate_appearance_id,
        pitch_number=pa_pitch_number,
        batter_card=batter_card,
        pitcher_card=pitcher_card,
        swing_type=swing_type,
        guessed_zone=guessed_zone,
        current_pitch=current_pitch,
        balls_before=balls_before,
        strikes_before=strikes_before,
        outs_before=outs_before,
        pitcher_fatigue=fatigue_factor,
        tactic_modifiers=tactics_modifiers if swing_type != "BUNT" else None,
        trace=trace,
        result=_event_value(raw_event),
    )

    # --- 7. Registrar evento en estadísticas ---
    if at_bat_ended:
        # Usar el runs_scored ya calculado en state_manager (evita recalcular un valor inconsistente)
        runs_scored = state.get("last_runs_scored", 0)
        rbi = runs_scored

        # Orden estructural de la jugada terminada dentro de la partida: ordinal
        # contiguo de los eventos de box score (1, 2, 3, …).
        event_sequence = state.get("event_sequence", 0) + 1
        state["event_sequence"] = event_sequence

        # La estadística forma parte de la misma unidad de trabajo que la
        # jugada. No se puede ocultar un error aquí: el caller debe revertir la
        # transacción para no dejar el marcador y el box score desincronizados.
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
            plate_appearance_id=plate_appearance_id,
            engine_version=ENGINE_BUILD,
            sequence_no=event_sequence,
        )

        # El PA terminó: la próxima identidad será un PA nuevo.
        state["plate_appearance_id"] = None
        state["pa_pitch_number"] = 0

    # --- 8. Preparar state final y evento WS diferido ---
    state["current_pitch"] = None
    state["last_event"] = event
    game.state_data = state

    # La persistencia pertenece al router; el evento queda en cola hasta que su
    # unidad de trabajo confirme.
    base_payload = build_play_resolved_payload(game, event, description, inning_completed=inning_ended, user_id=user_id, db=db)

    def _play_resolved_for(recipient_user_id: str) -> dict:
        # Fog of War por destinatario: cada jugador recibe su propia vista del state.
        player_state = sanitize_state_for_player(
            state_data=game.state_data,
            requesting_user_id=recipient_user_id,
            home_user_id=game.home_user_id,
            away_user_id=game.away_user_id,
            is_top_inning=game.is_top_inning,
        )
        player_state["user_role"] = "HOME" if recipient_user_id == game.home_user_id else "AWAY"
        payload = dict(base_payload)
        payload["state_data"] = player_state
        return payload

    await _publish_or_defer(
        PendingBroadcast("to_game_view", game_id, _play_resolved_for),
        pending_broadcasts,
    )
    return event, description, inning_ended


async def execute_cpu_pitcher_change(
    game: GameSession,
    state: dict,
    db,
    game_id: str,
    difficulty: str,
    *,
    pending_broadcasts: list[PendingBroadcast] | None = None,
) -> bool:
    """
    Ejecuta un cambio de pitcher CPU desde el bullpen congelado de la partida.

    Solo considera pitchers registrados en el snapshot HOME/AWAY y excluye el
    pitcher activo y los que ya participaron. Retorna True si se ejecutó el
    cambio, False si no hay relevistas disponibles.
    """
    cpu_is_home = game.home_user_id == "CPU_BOT"
    cpu_is_away = game.away_user_id == "CPU_BOT"
    
    if not (cpu_is_home or cpu_is_away):
        return False  # No hay CPU en este juego
    
    active_pitcher_id = state.get("active_pitcher")
    pitch_counts: dict = state.get("pitch_counts", {})
    used_pitcher_ids = set(pitch_counts.keys())
    
    bullpen_field = "home_bullpen" if cpu_is_home else "away_bullpen"
    bullpen_ids = state.get(bullpen_field, [])
    available = []
    for pitcher_id in bullpen_ids:
        if pitcher_id == active_pitcher_id or pitcher_id in used_pitcher_ids:
            continue
        pitcher = get_card_by_id(db, pitcher_id)
        if pitcher is None or not pitcher.is_pitcher:
            continue
        available.append(pitcher)
    
    logger.debug("CPU pitcher change: %s disponibles", len(available))
    for pitcher in available:
        logger.debug(
            "   %s (ID: %s) | Team: %s | OVR: %s | Pos: %s",
            pitcher.name, pitcher.id,
            pitcher.team.name if pitcher.team else "UNKNOWN",
            pitcher.overall, pitcher.position,
        )
    
    if not available:
        logger.warning("CPU pitcher change: no hay relevistas disponibles para el CPU")
        return False
    
    # Selección determinista: mejor OVR y desempate estable por id.
    new_pitcher = sorted(
        available,
        key=lambda pitcher: (-pitcher.overall, pitcher.id),
    )[0]
    logger.debug(
        "CPU pitcher change: seleccionado %s (OVR %s) | Team: %s (%s) | Pos: %s | Rarity: %s",
        new_pitcher.name, new_pitcher.overall,
        new_pitcher.team.name if new_pitcher.team else "UNKNOWN",
        new_pitcher.team_id, new_pitcher.position, new_pitcher.rarity,
    )
    
    # Ejecutar el cambio en state (regla compartida humano/CPU)
    old_pitcher_id = perform_pitcher_change(state, new_pitcher.id, is_home=cpu_is_home)

    # ⭐ Marcar que se está esperando confirmación del usuario
    state["awaiting_pitcher_change_acknowledgment"] = True
    state["pending_pitcher_change"] = {
        "old_pitcher_id": old_pitcher_id,
        "new_pitcher_id": new_pitcher.id,
    }

    # Persistir el estado en el objeto en memoria; el commit lo hace el router
    # que inició la acción (Unit of Work).
    game.state_data = state

    # Obtener datos del pitcher anterior
    old_pitcher = None
    old_pitcher_data = None
    if old_pitcher_id:
        old_pitcher = get_card_by_id(db, old_pitcher_id)
        if old_pitcher:
            old_pitcher_data = build_pitcher_payload(old_pitcher, with_repertoire=True)
    
    # Construir datos del nuevo pitcher para broadcast (entra descansado)
    new_pitcher_data = build_pitcher_payload(
        new_pitcher,
        with_repertoire=True,
        with_stamina=True,
        pitch_count=0,
        fatigue_level=0.0,
        fatigue_factor=1.0,
        fatigue_band=get_fatigue_band(1.0).value,
    )
    
    # Broadcast del cambio vía WebSocket (state_data sanitizado por destinatario)
    await _publish_or_defer(
        PendingBroadcast(
            "to_game_view",
            game_id,
            lambda u: {
                "type": "PITCHER_CHANGED",
                "message": f"🔄 La CPU ha hecho un cambio de pitcher. Entra: {new_pitcher.name}",
                "old_pitcher_id": old_pitcher_id,
                "old_pitcher_data": old_pitcher_data,
                "new_pitcher_id": new_pitcher.id,
                "new_pitcher": new_pitcher_data,
                "state_data": sanitize_state_for_player(
                    state_data=game.state_data,
                    requesting_user_id=u,
                    home_user_id=game.home_user_id,
                    away_user_id=game.away_user_id,
                    is_top_inning=game.is_top_inning,
                ),
            },
        ),
        pending_broadcasts,
    )

    return True


async def trigger_cpu_response(
    game: GameSession,
    state: dict,
    db,
    game_id: str,
    *,
    pending_broadcasts: list[PendingBroadcast] | None = None,
) -> None:
    """
    En partidas PvE, evalúa si le toca actuar a la CPU y ejecuta su acción.

    Caso A (batear): hay un picheo humano pendiente y el bateador activo es la CPU.
    Caso B (pichear): no hay picheo pendiente y el pitcher activo es la CPU (aquí
    también se evalúa si conviene un cambio de pitcher por fatiga).

    Estrategia (decidir/ruta) y persistencia están separadas: este módulo NUNCA
    commitea. El router que inició la acción humana es dueño de la transacción
    (Unit of Work), por lo que los cambios en memoria se persisten cuando el
    caller hace ``db.commit()``.
    """
    if state.get("mode") != "PVE" or state.get("is_game_over"):
        return

    difficulty = state.get("difficulty", "MEDIUM")
    cpu_batter_turn = is_cpu_turn(game, state, 'BATTER')
    cpu_pitcher_turn = is_cpu_turn(game, state, 'PITCHER')

    # Caso A: la CPU debe batear (hay un picheo humano pendiente)
    if cpu_batter_turn and state.get("current_pitch"):
        cpu_swing = get_cpu_swing_action(difficulty)
        await resolve_swing(
            game=game,
            state=state,
            swing_type=cpu_swing["swing_type"],
            guessed_zone=cpu_swing.get("guessed_zone"),
            guessed_pitch=cpu_swing.get("guessed_pitch"),
            db=db,
            game_id=game_id,
            user_id=None,  # CPU swing, sin user_id específico
            pending_broadcasts=pending_broadcasts,
        )
        # Tras el swing de la CPU puede haber cambiado la media entrada.
        state = dict(game.state_data or {})
        if state.get("is_game_over"):
            return

    # Caso B: la CPU debe pichear (no hay picheo pendiente y es el turno de la CPU)
    if cpu_pitcher_turn and not state.get("current_pitch"):
        # Evaluar si la CPU debe cambiar pitcher por fatiga
        active_pitcher_id = state.get("active_pitcher")
        if active_pitcher_id:
            pitch_count = state.get("pitch_counts", {}).get(active_pitcher_id, 0)
            pitcher_card = get_card_by_id(db, active_pitcher_id)

            if pitcher_card:
                total_innings = state.get("total_innings", 9)
                workload = get_workload(
                    pitch_count,
                    get_pitch_threshold(total_innings),
                )

                should_change = get_cpu_pitcher_change_decision(
                    pitch_count=pitch_count,
                    workload=workload,
                    difficulty=difficulty,
                )

                if should_change:
                    changed = await execute_cpu_pitcher_change(
                        game,
                        state,
                        db,
                        game_id,
                        difficulty,
                        pending_broadcasts=pending_broadcasts,
                    )
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

        await _publish_or_defer(
            PendingBroadcast(
                "to_game",
                game_id,
                {
                    "type": "PITCH_COMMITTED",
                    "message": "La CPU ha seleccionado su picheo. Es tu turno de batear.",
                    "has_pitched": True,
                },
            ),
            pending_broadcasts,
        )
