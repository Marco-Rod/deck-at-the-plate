from typing import Tuple, Dict, Any
from app.models import GameSession

def check_game_over(game: GameSession, state: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Verifica las condiciones de fin de juego según total_innings configurado:
    1. Walk-off: El local toma la delantera en la parte baja del último inning o posterior.
    2. Victoria Local Directa: Termina la alta del último inning con el local arriba (no se juega la baja).
    3. Cierre de Inning: Termina la baja del último inning (o posterior) con 3 outs y un ganador definido.
    El umbral de extra innings es total_innings + 1.
    """
    inning = game.current_inning
    is_top = game.is_top_inning
    score_home = game.score_home
    score_away = game.score_away

    # Leer la duración configurada del partido (default 9 si no está presente)
    total_innings = state.get("total_innings", 9)

    # Regla 1: Walk-off — El local anota y toma la delantera DURANTE la parte baja del último inning+.
    # La flag just_switched_half indica que acabamos de llegar a la baja sin haber bateado aún,
    # por lo que en ese momento no puede haber walk-off (el local no ha bateado todavía).
    if inning >= total_innings and not is_top and score_home > score_away and not state.get("just_switched_half"):
        return True, f"¡Victoria por WALK-OFF! El equipo local gana {score_home}-{score_away} en la entrada {inning}."

    # Regla 2: El local ya iba ganando al cerrar la parte alta del último inning → no se juega la baja.
    # Se detecta porque just_switched_half=True (recién cambiamos de alta a baja) y outs=0.
    if inning >= total_innings and not is_top and game.outs == 0 and score_home > score_away and state.get("just_switched_half"):
        return True, f"Juego finalizado. El equipo local gana {score_home}-{score_away} al cerrar la parte alta del inning {inning}."

    # Regla 3: Fin de la parte baja del último inning+ tras registrar los 3 outs.
    # Cuando se cierran los outs de la baja, state_manager ya incrementó current_inning.
    # Por tanto el inning que acaba de jugarse es (inning - 1), y debe ser >= total_innings.
    if inning > total_innings and is_top and state.get("just_switched_half"):
        prev_inning = inning - 1
        if score_away > score_home:
            return True, f"Juego finalizado. El equipo visitante gana {score_away}-{score_home} en {prev_inning} entradas."
        elif score_home > score_away:
            return True, f"Juego finalizado. El equipo local gana {score_home}-{score_away} en {prev_inning} entradas."

    return False, ""