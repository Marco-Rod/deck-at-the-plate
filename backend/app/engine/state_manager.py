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
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, Dict

from app.core.enums import Event, PitchType, RunnerBase
from app.core.engine_types import AtBatResult, Runners
from app.engine.runner_manager import advance_runners
from app.engine.game_over_manager import check_game_over
from app.engine.deck_manager import draw_card

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from app.models import GameSession


def process_at_bat_transition(
    game: "GameSession",
    event: str,
    state: Dict[str, Any],
    db: "Session" = None,
) -> AtBatResult:
    """
    Procesa el resultado de un swing/pitcheo y actualiza el estado completo del juego.

    Args:
        game:   Instancia de GameSession con campos outs, balls, strikes, score_*, inning, etc.
        event:  Evento producido por calculator.py (miembro de ``Event`` o su valor string).
        state:  Diccionario mutable state_data del GameSession.
        db:     Sesión opcional (solo usada para logs de pitcher al cambiar de media entrada).

    Returns:
        AtBatResult(at_bat_ended, inning_ended, final_event, description)
    """
    at_bat_ended = False
    inning_ended = False
    final_event = event
    description = ""  # Se actualiza con la descripción del evento

    # Limpiar la flag de cambio de media entrada del turno anterior
    state["just_switched_half"] = False

    # --- FASE 1: Acumulación de Conteo ---
    if event in (Event.STRIKE_SWINGING, Event.STRIKE_LOOKING):
        game.strikes += 1
    elif event == Event.BALL:
        # ⭐ NUEVO: Si es IBB (base intencional), saltamos directo a 4 bolas
        current_pitch = state.get("current_pitch", {})
        actual_pitch = current_pitch.get("pitch_type") if isinstance(current_pitch, dict) else None

        if actual_pitch == PitchType.IBB:
            game.balls = 4  # Forzar a 4 para que se detecte como WALK instantáneamente
        else:
            game.balls += 1
    elif event == Event.FOUL and game.strikes < 2:
        # El foul solo suma strike si el bateador tiene menos de 2 strikes
        game.strikes += 1

    # --- FASE 2: Evaluación de Cierre de At-Bat ---

    # A. Ponche (3 strikes)
    if game.strikes >= 3:
        game.outs += 1
        final_event = Event.STRIKEOUT
        at_bat_ended = True

    # B. Base por bolas (4 bolas)
    elif game.balls >= 4:
        final_event = Event.WALK
        at_bat_ended = True

    # C. Bola en juego (hits y outs directos)
    elif event in (
        Event.HIT_1B, Event.HIT_2B, Event.HIT_3B,
        Event.HOME_RUN, Event.OUT_FLY, Event.OUT_GROUND,
    ):
        at_bat_ended = True
        if event in (Event.OUT_FLY, Event.OUT_GROUND):
            game.outs += 1

    # --- FASE 3: Avance de corredores y anotación de carreras ---
    # Solo aplica cuando el at-bat termina con un evento que mueve corredores
    # Excluye: STRIKEOUT (no mueve corredores)
    # Incluye: OUT_GROUND (puede ser double play), OUT_FLY, HIT_*, WALK, HOME_RUN
    if at_bat_ended and final_event != Event.STRIKEOUT:
        # Asegurar que runners tiene todas las claves necesarias
        current_runners: Runners = state.get("runners", {})
        if not isinstance(current_runners, dict):
            current_runners = {}

        # Garantizar que existen todas las claves
        for base in (RunnerBase.FIRST, RunnerBase.SECOND, RunnerBase.THIRD):
            if base not in current_runners:
                current_runners[base] = None

        active_batter = state.get("active_batter", "BATTER")

        print(f"🏃 [RUNNER ADVANCE] event={final_event}, batter={active_batter}, runners_before={current_runners}")

        # IMPORTANTE: advance_runners ahora retorna 3 valores (runners, runs, event_adjusted)
        # El event_adjusted puede ser "DOUBLE_PLAY" si se logró un doble play
        updated_runners, runs_scored, event_adjusted = advance_runners(current_runners, final_event, active_batter)

        # Asegurar que el resultado también tiene todas las claves
        for base in (RunnerBase.FIRST, RunnerBase.SECOND, RunnerBase.THIRD):
            if base not in updated_runners:
                updated_runners[base] = None

        state["runners"] = updated_runners

        # Si fue doble play, sumar out adicional
        if event_adjusted == Event.DOUBLE_PLAY:
            game.outs += 1  # Segundo out del doble play
            final_event = Event.DOUBLE_PLAY
            print(f"⚾ [DOUBLE PLAY] ¡Doble play! Outs ahora: {game.outs}")

        print(f"✅ [RUNNERS UPDATED] runners_after={updated_runners}, runs_scored={runs_scored}, event={event_adjusted}")

        # --- VALIDACIÓN CRÍTICA: Inning-Ending Double Play Rule ---
        # En béisbol, una carrera SOLO cuenta si cruza home ANTES del 3er out
        # Ejemplo: Bases llenas, 2 outs → Doble play completa 3 outs
        #   El corredor en 3B NO anota porque el 3er out se completa en el DP
        if runs_scored > 0 and game.outs >= 3:
            # El tercer out ya se completó → ninguna carrera cuenta
            print(f"⚾ [INNING-ENDING DP] 3er out completado. Carreras anuladas: {runs_scored} → 0")
            runs_scored = 0

        if runs_scored > 0:
            if game.is_top_inning:
                game.score_away += runs_scored  # Visita anota en la Alta
                print(f"⭐ [SCORE UPDATE] TOP INNING: score_away += {runs_scored} → now {game.score_away}")
            else:
                game.score_home += runs_scored  # Local anota en la Baja
                print(f"⭐ [SCORE UPDATE] BOT INNING: score_home += {runs_scored} → now {game.score_home}")

        # ⭐ NUEVO: Guardar runs_scored en el estado para que gameplay.py lo use
        # en lugar de recalcularlo (evita inconsistencias)
        state["last_runs_scored"] = runs_scored

        # ⭐ NUEVO: Rastrear carreras por inning en score_history
        if "score_history" not in state:
            state["score_history"] = {}

        inning_key = f"{game.current_inning}_{str(game.is_top_inning).lower()}"
        if inning_key not in state["score_history"]:
            state["score_history"][inning_key] = 0

        state["score_history"][inning_key] += runs_scored
        print(f"📊 [SCORE HISTORY] {inning_key}: +{runs_scored} → total {state['score_history'][inning_key]}")

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

            # ⭐ IMPORTANTE: Limpiar current_pitch al cambiar de inning
            state["current_pitch"] = None

            if game.is_top_inning:
                # Alta → Baja: el mismo inning, ahora batea el local
                game.is_top_inning = False
            else:
                # Baja → Alta: avanza al siguiente inning, batea el visitante
                game.is_top_inning = True
                game.current_inning += 1

            # Al cambiar de media entrada, actualizar el pitcher y el primer bateador activos.
            # En la Alta (is_top_inning=True): home lanza, away batea.
            # En la Baja (is_top_inning=False): away lanza, home batea.
            if game.is_top_inning:
                # Recién pasamos a la Alta: home_pitcher lanza, primer bateador away batea
                home_pitcher = state.get("home_pitcher_id") or state.get("active_pitcher")
                state["active_pitcher"] = home_pitcher
                away_idx = state.get("away_batter_index", 0)
                away_lineup = state.get("away_lineup", [])
                if away_lineup:
                    state["active_batter"] = away_lineup[away_idx]

                # Log: qué pitcher está en el montículo en la Alta
                # (la dependencia ORM solo vive en el path con sesión de BD)
                if db:
                    from app.models import PlayerCardModel
                    pitcher_card = db.query(PlayerCardModel).filter(PlayerCardModel.id == home_pitcher).first()
                else:
                    pitcher_card = None
                print(f"🔄 [INNING CHANGE] → ALTA de Inning {game.current_inning}")
                print(f"   HOME pitcher al montículo: {pitcher_card.name if pitcher_card else 'UNKNOWN'} ({home_pitcher})")
            else:
                # Recién pasamos a la Baja: away_pitcher lanza, primer bateador home batea
                away_pitcher = state.get("away_pitcher_id") or state.get("active_pitcher")
                state["active_pitcher"] = away_pitcher
                home_idx = state.get("home_batter_index", 0)
                home_lineup = state.get("home_lineup", [])
                if home_lineup:
                    state["active_batter"] = home_lineup[home_idx]

                # Log: qué pitcher está en el montículo en la Baja
                # (la dependencia ORM solo vive en el path con sesión de BD)
                if db:
                    from app.models import PlayerCardModel
                    pitcher_card = db.query(PlayerCardModel).filter(PlayerCardModel.id == away_pitcher).first()
                else:
                    pitcher_card = None
                print(f"🔄 [INNING CHANGE] → BAJA de Inning {game.current_inning}")
                print(f"   AWAY pitcher al montículo: {pitcher_card.name if pitcher_card else 'UNKNOWN'} ({away_pitcher})")

            # --- Ghost runner en extra innings ---
            # Se coloca al inicio de cada media entrada a partir del inning total_innings+1.
            # El corredor es el último bateador que hizo out en la media entrada anterior.
            total_innings = state.get("total_innings", 9)
            if game.current_inning >= total_innings + 1:
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
        final_event = Event.GAME_OVER

    # --- Generar descripción según el evento ---
    if final_event == Event.GAME_OVER:
        # GAME_OVER: usar el mensaje de ganador almacenado en estado
        description = state.get("winner_message", "¡Fin del juego!")
    elif final_event == Event.DOUBLE_PLAY:
        description = "¡Doble play! El corredor en primera fue eliminado y el bateador también."
    elif final_event == Event.STRIKEOUT:
        description = "Strikeout! El bateador no pudo conectar."
    elif final_event == Event.STRIKE_LOOKING:
        description = "Lanzamiento en la zona. ¡Strike cantado!"
    elif final_event == Event.STRIKE_SWINGING:
        description = "Swing abanicado. ¡Strike!"
    elif final_event == Event.OUT_GROUND:
        description = "Roletazo al cuadro para out."
    elif final_event == Event.OUT_FLY:
        description = "Elevado de rutina atrapado en el jardín."
    elif final_event == Event.FOUL:
        description = "Batazo de foul."
    elif final_event == Event.BALL:
        description = "Bola."
    elif final_event == Event.HIT_1B:
        description = "Hit sencillo."
    elif final_event == Event.HIT_2B:
        description = "Doble base."
    elif final_event == Event.HIT_3B:
        description = "Triple."
    elif final_event == Event.HOME_RUN:
        description = "¡HOME RUN!"
    elif final_event == Event.WALK:
        description = "Base por bolas."
    else:
        description = final_event  # Para otros eventos, usar el nombre del evento

    # Añadir notificación de cambio de entrada si es necesario
    if inning_ended:
        description += " Tres outs registrados. Cambio de entrada."

    return AtBatResult(at_bat_ended, inning_ended, final_event, description)