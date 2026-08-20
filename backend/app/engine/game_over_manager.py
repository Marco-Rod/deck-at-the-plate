from typing import Tuple, Dict, Any
from app.models import GameSession

def check_game_over(game: GameSession, state: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Verifica las condiciones de fin de juego (Novena entrada o Extra Innings):
    1. Walk-off: El local toma la delantera en la parte baja de la 9na o posterior.
    2. Victoria Local Directa: Termina la alta de la 9na con el local arriba en la pizarra.
    3. Cierre de Inning: Termina la baja de la 9na (o posterior) con 3 outs y un ganador definido.
    """
    inning = game.current_inning
    is_top = game.is_top_inning
    score_home = game.score_home
    score_away = game.score_away

    # Regla 1: Walk-off (En cualquier momento de la parte baja de la 9na+, el local toma la delantera)
    if inning >= 9 and not is_top and score_home > score_away:
        return True, f"¡Victoria por WALK-OFF! El equipo local gana {score_home}-{score_away} en la entrada {inning}."

    # Regla 2: Fin de la parte alta de la 9na+ si el local ya va ganando (No se juega la parte baja)
    if inning >= 9 and not is_top and game.outs == 0 and score_home > score_away and state.get("just_switched_half"):
        return True, f"Juego finalizado. El equipo local gana {score_home}-{score_away} al cerrar la parte alta."

    # Regla 3: Fin de la parte baja de la 9na+ tras registrar los 3 outs
    if inning >= 9 and is_top and state.get("just_switched_half"):  # Ya cambió al siguiente inning
        prev_inning = inning - 1
        if score_away > score_home:
            return True, f"Juego finalizado. El equipo visitante gana {score_away}-{score_home} en {prev_inning} entradas."
        elif score_home > score_away:
            return True, f"Juego finalizado. El equipo local gana {score_home}-{score_away} en {prev_inning} entradas."

    return False, ""