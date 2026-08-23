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
    (at_bat_ended: bool, inning_ended: bool, final_event: str)
"""

from typing import Dict, Any, Tuple
from app.models import GameSession
from app.engine.runner_manager import advance_runners
from app.engine.game_over_manager import check_game_over
from app.engine.deck_manager import draw_card


def process_at_bat_transition(
    game: GameSession,
    event: str,
    state: Dict[str, Any]
) -> Tuple[bool, bool, str]:
    """
    Procesa el resultado de un swing/pitcheo y actualiza el estado completo del juego.

    Args:
        game:   Instancia de GameSession con campos outs, balls, strikes, score_*, inning, etc.
        event:  Código del evento producido por calculator.py (ej. "STRIKE_SWINGING", "HIT_1B").
        state:  Diccionario mutable state_data del GameSession.

    Returns:
        at_bat_ended (bool):  True si el turno del bateador terminó (out, hit, walk, strikeout).
        inning_ended (bool):  True si se alcanzaron 3 outs y cambió la media entrada.
        final_event (str):    Evento ajustado. Ej. 3 STRIKE_SWINGING → "STRIKEOUT".
    """
    at_bat_ended = False
    inning_ended = False
    final_event = event

    # Limpiar la flag de cambio de media entrada del turno anterior
    state["just_switched_half"] = False

    # --- FASE 1: Acumulación de Conteo ---
    if event in ("STRIKE_SWINGING", "STRIKE_LOOKING"):
        game.strikes += 1
    elif event == "BALL":
        game.balls += 1
    elif event == "FOUL" and game.strikes < 2:
        # El foul solo suma strike si el bateador tiene menos de 2 strikes
        game.strikes += 1

    # --- FASE 2: Evaluación de Cierre de At-Bat ---

    # A. Ponche (3 strikes)
    if game.strikes >= 3:
        game.outs += 1
        final_event = "STRIKEOUT"
        at_bat_ended = True

    # B. Base por bolas (4 bolas)
    elif game.balls >= 4:
        final_event = "WALK"
        at_bat_ended = True

    # C. Bola en juego (hits y outs directos)
    elif event in ("HIT_1B", "HIT_2B", "HIT_3B", "HOME_RUN", "OUT_FLY", "OUT_GROUND"):
        at_bat_ended = True
        if event in ("OUT_FLY", "OUT_GROUND"):
            game.outs += 1

    # --- FASE 3: Avance de corredores y anotación de carreras ---
    # Solo aplica cuando el at-bat termina con un evento que mueve corredores
    # (excluye strikeout y outs directos que no producen avance)
    if at_bat_ended and final_event not in ("STRIKEOUT", "OUT_FLY", "OUT_GROUND"):
        current_runners = state.get("runners", {"1b": None, "2b": None, "3b": None})
        active_batter = state.get("active_batter", "BATTER")

        updated_runners, runs_scored = advance_runners(current_runners, final_event, active_batter)
        state["runners"] = updated_runners

        if runs_scored > 0:
            if game.is_top_inning:
                game.score_away += runs_scored  # Visita anota en la Alta
            else:
                game.score_home += runs_scored  # Local anota en la Baja

    # --- FASE 4: Limpieza del at-bat y rotación del lineup ---
    if at_bat_ended:
        game.balls = 0
        game.strikes = 0

        # Resetear tácticas activas del turno
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

        # --- FASE 5: Cambio de media entrada (3 outs) ---
        if game.outs >= 3:
            game.outs = 0
            inning_ended = True

            # Marcar que acabamos de cambiar de media entrada para game_over_manager
            state["just_switched_half"] = True

            # Limpiar bases al cambiar de media entrada
            state["runners"] = {"1b": None, "2b": None, "3b": None}

            if game.is_top_inning:
                # Alta → Baja: el mismo inning, ahora batea el local
                game.is_top_inning = False
            else:
                # Baja → Alta: avanza al siguiente inning, batea el visitante
                game.is_top_inning = True
                game.current_inning += 1

            # --- Ghost runner en extra innings ---
            # Solo se coloca al inicio de cada media entrada a partir del inning 10.
            # El corredor es el último bateador que hizo out en la media entrada anterior.
            if game.current_inning >= 10:
                ghost_runner_id = state.get("last_out_batter", "GHOST_RUNNER")
                state["runners"] = {"1b": None, "2b": ghost_runner_id, "3b": None}

            # Repartir carta táctica adicional a ambos equipos al cambiar de entrada
            if "tactics" in state:
                draw_card(state["tactics"], "home")
                draw_card(state["tactics"], "away")

    # --- FASE 6: Evaluación de condición de fin de juego ---
    is_over, message = check_game_over(game, state)
    if is_over:
        state["is_game_over"] = True
        state["winner_message"] = message
        final_event = "GAME_OVER"

    return at_bat_ended, inning_ended, final_event
