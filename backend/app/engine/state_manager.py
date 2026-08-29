"""
Módulo: state_manager
======================
Máquina de estados central del at-bat. Procesa el resultado de cada jugada
y actualiza todos los campos del GameSession y state_data correspondientes.

Responsabilidades:
    1. Acumular el conteo de bolas, strikes y fouls.
    2. Cerrar el at-bat cuando se alcanza el límite (3 strikes, 4 bolas, hit en juego, out directo).
    3. Avanzar corredores y sumar carreras al marcador mediante runner_manager.
    4. Rotar el lineup al siguiente bateador.
    5. Detectar el cambio de media entrada (3 outs) y alternar is_top_inning / current_inning.
    6. Colocar el ghost runner en segunda base al inicio de cada media entrada en extra innings.
    7. Establecer la flag just_switched_half para que game_over_manager pueda evaluar
       las condiciones de fin de juego que dependen del cambio de media entrada.
    8. Repartir una carta táctica adicional a cada equipo al cambiar de entrada.
    9. Llamar a check_game_over al final de cada jugada.

Retorna:
    Un ``AtBatResult`` con (at_bat_ended, inning_ended, final_event, description).

Sobre la capa de datos: este módulo es PURA (sin SQLAlchemy). El antiguo
parámetro ``db`` (solo usado para logs de nombre de pitcher) se eliminó; los
logs de cambio de media entrada usan únicamente los ids del state_data.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict, Tuple

from app.core.enums import Event, PitchType, RunnerBase
from app.core.engine_types import AtBatResult, Runners
from app.engine.runner_manager import advance_runners
from app.engine.game_over_manager import check_game_over
from app.engine.deck_manager import draw_card

if TYPE_CHECKING:
    from app.models import GameSession

# Descripciones por evento (Open/Closed: agregar evento = añadir entrada aquí).
_DESCRIPTIONS: Dict[Any, str] = {
    Event.DOUBLE_PLAY: "¡Doble play! El corredor en primera fue eliminado y el bateador también.",
    Event.STRIKEOUT: "Strikeout! El bateador no pudo conectar.",
    Event.STRIKE_LOOKING: "Lanzamiento en la zona. ¡Strike cantado!",
    Event.STRIKE_SWINGING: "Swing abanicado. ¡Strike!",
    Event.OUT_GROUND: "Roletazo al cuadro para out.",
    Event.OUT_FLY: "Elevado de rutina atrapado en el jardín.",
    Event.FOUL: "Batazo de foul.",
    Event.BALL: "Bola.",
    Event.HIT_1B: "Hit sencillo.",
    Event.HIT_2B: "Doble base.",
    Event.HIT_3B: "Triple.",
    Event.HOME_RUN: "¡HOME RUN!",
    Event.WALK: "Base por bolas.",
}


def end_half_inning(game: "GameSession", state: Dict[str, Any]) -> None:
    """
    Cambio de media entrada (3 outs).

    Fuente única compartida por el flujo normal del at-bat y por ``steal_attempt``:
    resetea conteo y corredores, alterna la media entrada, activa el pitcher y el
    primer bateador correctos del nuevo half, coloca el ghost runner en extra
    innings y reparte la carta táctica adicional.

    El caller es responsable de marcar ``inning_ended``.
    """
    game.outs = 0
    game.balls = 0
    game.strikes = 0
    state["just_switched_half"] = True

    # Limpiar bases y el picheo pendiente al cambiar de media entrada
    state["runners"] = {"1b": None, "2b": None, "3b": None}
    state["current_pitch"] = None

    if game.is_top_inning:
        # Alta → Baja: el mismo inning, ahora batea el local
        game.is_top_inning = False
    else:
        # Baja → Alta: avanza al siguiente inning, batea el visitante
        game.is_top_inning = True
        game.current_inning += 1

    # Actualizar el pitcher y el primer bateador activos del nuevo half.
    # En la Alta (is_top_inning=True): home lanza, away batea.
    # En la Baja (is_top_inning=False): away lanza, home batea.
    if game.is_top_inning:
        home_pitcher = state.get("home_pitcher_id") or state.get("active_pitcher")
        state["active_pitcher"] = home_pitcher
        away_idx = state.get("away_batter_index", 0)
        away_lineup = state.get("away_lineup", [])
        if away_lineup:
            state["active_batter"] = away_lineup[away_idx]
        print(f"🔄 [INNING CHANGE] → ALTA de Inning {game.current_inning}")
        print(f"   HOME pitcher al montículo: {home_pitcher}")
    else:
        away_pitcher = state.get("away_pitcher_id") or state.get("active_pitcher")
        state["active_pitcher"] = away_pitcher
        home_idx = state.get("home_batter_index", 0)
        home_lineup = state.get("home_lineup", [])
        if home_lineup:
            state["active_batter"] = home_lineup[home_idx]
        print(f"🔄 [INNING CHANGE] → BAJA de Inning {game.current_inning}")
        print(f"   AWAY pitcher al montículo: {away_pitcher}")

    # Ghost runner en extra innings (a partir de total_innings+1).
    # El corredor es el último bateador que hizo out en la media entrada anterior.
    total_innings = state.get("total_innings", 9)
    if game.current_inning >= total_innings + 1:
        ghost_runner_id = state.get("last_out_batter", "GHOST_RUNNER")
        state["runners"] = {"1b": None, "2b": ghost_runner_id, "3b": None}

    # Repartir carta táctica adicional a ambos equipos al cambiar de entrada
    if "tactics" in state:
        draw_card(state["tactics"], "home")
        draw_card(state["tactics"], "away")


def _accumulate_count(game: "GameSession", state: Dict[str, Any], event: str) -> None:
    """FASE 1: acumula bolas, strikes y fouls del conteo."""
    if event in (Event.STRIKE_SWINGING, Event.STRIKE_LOOKING):
        game.strikes += 1
    elif event == Event.BALL:
        # IBB (base intencional) → saltar directo a 4 bolas
        current_pitch = state.get("current_pitch", {})
        actual_pitch = current_pitch.get("pitch_type") if isinstance(current_pitch, dict) else None
        if actual_pitch == PitchType.IBB:
            game.balls = 4
        else:
            game.balls += 1
    elif event == Event.FOUL and game.strikes < 2:
        # El foul solo suma strike si el bateador tiene menos de 2 strikes
        game.strikes += 1


def _evaluate_at_bat_close(game: "GameSession", event: str) -> Tuple[bool, str]:
    """
    FASE 2: decide si el at-bat termina y con qué evento final.

    Retorna (at_bat_ended, final_event).
    """
    # A. Ponche (3 strikes)
    if game.strikes >= 3:
        game.outs += 1
        return True, Event.STRIKEOUT

    # B. Base por bolas (4 bolas)
    if game.balls >= 4:
        return True, Event.WALK

    # C. Bola en juego (hits y outs directos)
    if event in (
        Event.HIT_1B, Event.HIT_2B, Event.HIT_3B,
        Event.HOME_RUN, Event.OUT_FLY, Event.OUT_GROUND,
    ):
        if event in (Event.OUT_FLY, Event.OUT_GROUND):
            game.outs += 1
        return True, event

    return False, event


def _advance_runners_and_score(
    game: "GameSession", final_event: str, state: Dict[str, Any]
) -> str:
    """
    FASE 3: avanza corredores y anota carreras cuando el at-bat terminó con un
    evento que mueve corredores. Retorna el evento final (puede ajustarse a
    DOUBLE_PLAY).
    """
    if final_event == Event.STRIKEOUT:
        return final_event

    # Asegurar que runners tiene todas las claves necesarias
    current_runners: Runners = state.get("runners", {})
    if not isinstance(current_runners, dict):
        current_runners = {}
    for base in (RunnerBase.FIRST, RunnerBase.SECOND, RunnerBase.THIRD):
        if base not in current_runners:
            current_runners[base] = None

    active_batter = state.get("active_batter", "BATTER")
    updated_runners, runs_scored, event_adjusted = advance_runners(current_runners, final_event, active_batter)

    for base in (RunnerBase.FIRST, RunnerBase.SECOND, RunnerBase.THIRD):
        if base not in updated_runners:
            updated_runners[base] = None
    state["runners"] = updated_runners

    # Si fue doble play, sumar out adicional
    if event_adjusted == Event.DOUBLE_PLAY:
        game.outs += 1  # Segundo out del doble play
        final_event = Event.DOUBLE_PLAY

    # Inning-Ending Double Play Rule: una carrera SOLO cuenta si cruza home
    # ANTES del 3er out. Si el 3er out se completa en el DP, las carreras se anulan.
    if runs_scored > 0 and game.outs >= 3:
        runs_scored = 0

    if runs_scored > 0:
        if game.is_top_inning:
            game.score_away += runs_scored  # Visita anota en la Alta
        else:
            game.score_home += runs_scored  # Local anota en la Baja

    # Guardar runs_scored para que los callers no lo recalculen (evita inconsistencias)
    state["last_runs_scored"] = runs_scored

    # Rastrear carreras por inning en score_history
    state.setdefault("score_history", {})
    inning_key = f"{game.current_inning}_{str(game.is_top_inning).lower()}"
    state["score_history"][inning_key] = state["score_history"].get(inning_key, 0) + runs_scored

    return final_event


def _rotate_batter(game: "GameSession", state: Dict[str, Any]) -> None:
    """FASE 4: resetea el conteo, limpia tácticas y rota al siguiente bateador."""
    game.balls = 0
    game.strikes = 0
    state["active_tactics"] = {"home": None, "away": None}

    # Guardar el bateador que terminó el at-bat (necesario para ghost runner en extra innings)
    state["last_out_batter"] = state.get("active_batter", "GHOST_RUNNER")

    # Rotar al siguiente bateador en el orden del equipo ofensivo
    if game.is_top_inning:
        curr_idx = state.get("away_batter_index", 0)
        next_idx = (curr_idx + 1) % 9
        state["away_batter_index"] = next_idx
        state["active_batter"] = state["away_lineup"][next_idx]
    else:
        curr_idx = state.get("home_batter_index", 0)
        next_idx = (curr_idx + 1) % 9
        state["home_batter_index"] = next_idx
        state["active_batter"] = state["home_lineup"][next_idx]


def _describe_event(final_event: str, state: Dict[str, Any]) -> str:
    """Genera la descripción legible del evento final."""
    if final_event == Event.GAME_OVER:
        return state.get("winner_message", "¡Fin del juego!")
    return _DESCRIPTIONS.get(final_event, final_event)


def process_at_bat_transition(
    game: "GameSession",
    event: str,
    state: Dict[str, Any],
) -> AtBatResult:
    """
    Procesa el resultado de un swing/pitcheo y actualiza el estado completo del juego.

    Args:
        game:   Instancia de GameSession con campos outs, balls, strikes, score_*, inning, etc.
        event:  Evento producido por calculator.py (miembro de ``Event`` o su valor string).
        state:  Diccionario mutable state_data del GameSession.

    Returns:
        AtBatResult(at_bat_ended, inning_ended, final_event, description)
    """
    at_bat_ended = False
    inning_ended = False
    final_event = event
    description = ""

    # Limpiar la flag de cambio de media entrada del turno anterior
    state["just_switched_half"] = False

    # FASE 1: Acumulación de conteo
    _accumulate_count(game, state, event)

    # FASE 2: Evaluación de cierre de at-bat
    at_bat_ended, final_event = _evaluate_at_bat_close(game, event)

    # FASE 3: Avance de corredores y anotación de carreras
    if at_bat_ended and final_event != Event.STRIKEOUT:
        final_event = _advance_runners_and_score(game, final_event, state)

    # FASE 4+5: Limpieza del at-bat, rotación del lineup y cambio de media entrada
    if at_bat_ended:
        _rotate_batter(game, state)
        if game.outs >= 3:
            inning_ended = True
            end_half_inning(game, state)

    # FASE 6: Evaluación de condición de fin de juego
    is_over, message = check_game_over(game, state)
    if is_over:
        state["is_game_over"] = True
        state["winner_message"] = message
        final_event = Event.GAME_OVER

    # Descripción según el evento
    description = _describe_event(final_event, state)

    # Notificación de cambio de entrada si es necesario
    if inning_ended:
        description += " Tres outs registrados. Cambio de entrada."

    return AtBatResult(at_bat_ended, inning_ended, final_event, description)