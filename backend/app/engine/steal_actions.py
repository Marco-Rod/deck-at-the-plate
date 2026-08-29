"""
Acción de dominio: robo de base
================================
Resuelve el intento de robo (2B/3B) y aplica sus consecuencias sobre el estado
de la partida: avance de corredores, conteo de outs y, si aplica, el cambio de
media entrada con sus reglas (reset de conteo/corredores y evaluación de fin de
juego). Es lógica PURA: sin FastAPI, sin sesión de BD ni broadcasts.
"""
from typing import TYPE_CHECKING, Any, Dict, Tuple

from app.engine.tactical_actions import resolve_steal
from app.engine.state_manager import end_half_inning
from app.engine.game_over_manager import check_game_over

if TYPE_CHECKING:
    from app.models import GameSession

_DEFAULT_RUNNERS = {"1b": None, "2b": None, "3b": None}


def steal_attempt(
    game: "GameSession",
    state: Dict[str, Any],
    target_base: str,
    pitcher_attrs: dict,
) -> Tuple[bool, str]:
    """
    Ejecuta el intento de robo y muta ``game``/``state`` con sus consecuencias.

    Returns:
        (success, description)
    """
    runners = state.get("runners", dict(_DEFAULT_RUNNERS))
    success, description = resolve_steal(pitcher_attrs, runners, target_base)

    from_base = "1b" if target_base == "2b" else "2b"

    if success:
        runners[target_base] = runners[from_base]
        runners[from_base] = None
    else:
        # Out por robo fallido (Caught Stealing)
        runners[from_base] = None
        game.outs += 1

        if game.outs >= 3:
            # Cambio de media entrada vía la fuente única (reset de conteo,
            # corredores, alternancia de innings, swap de pitcher/bateador,
            # ghost runner y cartas tácticas).
            end_half_inning(game, state)
            description += " Tres outs registrados. Cambio de entrada."

            # end_half_inning ya limpió las bases: conservar esa limpieza y no
            # permitir que el dict local reintroduzca corredores al asignarse abajo.
            runners = dict(state["runners"])

            # Verificar fin de juego tras el out por robo
            is_over, win_msg = check_game_over(game, state)
            if is_over:
                state["is_game_over"] = True
                state["winner_message"] = win_msg
        else:
            state["just_switched_half"] = False

    state["runners"] = runners
    return success, description