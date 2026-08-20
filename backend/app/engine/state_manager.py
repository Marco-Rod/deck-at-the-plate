from typing import Dict, Any, Tuple
from app.models import GameSession
from app.engine.runner_manager import advance_runners
from app.engine.game_over_manager import check_game_over
from app.engine.deck_manager import draw_card

def process_at_bat_transition(game: GameSession, event: str, state: Dict[str, Any]) -> Tuple[bool, bool, str]:
    """
    Procesa el resultado de un swing/pitcheo y actualiza outs, bolas, strikes e inning.
    
    Retorna:
        - at_bat_ended (bool): Indica si terminó el turno del bateador actual.
        - inning_ended (bool): Indica si cayeron los 3 outs y cambió la media entrada.
        - final_event (str): Evento ajustado (ej. convierte 3 strikes a 'STRIKEOUT').
    """
    at_bat_ended = False
    inning_ended = False
    final_event = event

    # --- FASE 1: Acumulación de Conteo ---
    if event in ["STRIKE_SWINGING", "STRIKE_LOOKING"]:
        game.strikes += 1
    elif event == "BALL":
        game.balls += 1
    elif event == "FOUL" and game.strikes < 2:
        game.strikes += 1

    # --- FASE 2: Evaluación de Cierre de At-Bat ---
    # A. Ponche / Strikeout (3 Strikes)
    if game.strikes >= 3:
        game.outs += 1
        final_event = "STRIKEOUT"
        at_bat_ended = True

    # B. Base por Bolas / Walk (4 Bolas)
    elif game.balls >= 4:
        final_event = "WALK"
        at_bat_ended = True

    # C. Conexiones e Impactos en Juego (Hits y Outs directos)
    elif event in ["HIT_1B", "HIT_2B", "HIT_3B", "HOME_RUN", "OUT_FLY", "OUT_GROUND"]:
        at_bat_ended = True
        if event in ["OUT_FLY", "OUT_GROUND"]:
            game.outs += 1

    # --- FASE 3: Limpieza de Estado de At-Bat ---
    if at_bat_ended and final_event not in ["STRIKEOUT", "OUT_FLY", "OUT_GROUND"]:
        current_runners = state.get("runners", {"1b": None, "2b": None, "3b": None})
        active_batter = state.get("active_batter", "BATTER")
        
        updated_runners, runs_scored = advance_runners(current_runners, final_event, active_batter)
        
        # Guardar nuevo estado de bases
        state["runners"] = updated_runners

        # Sumar carreras al marcador
        if runs_scored > 0:
            if game.is_top_inning:
                game.score_away += runs_scored
            else:
                game.score_home += runs_scored

    # --- FASE 4: Limpieza de Estado de At-Bat ---
    if at_bat_ended:
        game.balls = 0
        game.strikes = 0
        # Resetear modificadores tácticos aplicados en el turno
        state["active_tactics"] = {"home": None, "away": None}

        # Rotar al siguiente bateador del equipo que está actualmente al bate
        if game.is_top_inning:
            # Batea el equipo visitante
            curr_idx = state.get("away_batter_index", 0)
            next_idx = (curr_idx + 1) % 9
            state["away_batter_index"] = next_idx
            state["active_batter"] = state["away_lineup"][next_idx]
        else:
            # Batea el equipo local
            curr_idx = state.get("home_batter_index", 0)
            next_idx = (curr_idx + 1) % 9
            state["home_batter_index"] = next_idx
            state["active_batter"] = state["home_lineup"][next_idx]

        # --- FASE 4: Evaluación de Cambio de Entrada (3 Outs) ---
        if game.outs >= 3:
            game.outs = 0
            inning_ended = True
            
            # Limpiar corredores en bases
            state["runners"] = {"1b": None, "2b": None, "3b": None}

            # Alternar media entrada
            if game.is_top_inning:
                game.is_top_inning = False  # Pasa a la Baja del inning
            else:
                game.is_top_inning = True   # Pasa a la Alta del siguiente inning
                game.current_inning += 1

    # 5. Evaluar Condición de Fin de Juego (Game Over)
    is_over, message = check_game_over(game, state)
    if is_over:
        state["is_game_over"] = True
        state["winner_message"] = message
        final_event = "GAME_OVER"

    # Al cambiar de media entrada:
    if game.current_inning >= 10:
        # Corredor automático en segunda base
        state["runners"] = {"1b": None, "2b": state.get("last_out_batter", "GHOST_RUNNER"), "3b": None}
    else:
        state["runners"] = {"1b": None, "2b": None, "3b": None}

    if inning_ended:
        draw_card(state["tactics"], "home")
        draw_card(state["tactics"], "away")

    return at_bat_ended, inning_ended, final_event