from typing import Dict, Any

PITCH_THRESHOLD_STARTER = 60  # Umbral de lanzamientos antes de empezar a fatigarse
FATIGUE_PENALTY_STEP = 15     # Cada 15 lanzamientos extra aplica penalización

def apply_pitcher_fatigue(
    pitcher_attrs: Dict[str, int], 
    pitch_count: int
) -> Dict[str, int]:
    """
    Aplica penalizaciones a Velocidad, Control y Movimiento si el picher
    ha superado su umbral de lanzamientos en la partida.
    """
    modified_attrs = pitcher_attrs.copy()

    if pitch_count > PITCH_THRESHOLD_STARTER:
        extra_pitches = pitch_count - PITCH_THRESHOLD_STARTER
        # Penalización: -3% en atributos por cada tramo de 15 picheos extra
        penalty_factor = 1.0 - (0.03 * (extra_pitches // FATIGUE_PENALTY_STEP + 1))
        penalty_factor = max(0.5, penalty_factor)  # Límite máximo de degradación: -50%

        modified_attrs["velocidad"] = int(modified_attrs.get("velocidad", 50) * penalty_factor)
        modified_attrs["control"] = int(modified_attrs.get("control", 50) * penalty_factor)
        modified_attrs["movimiento"] = int(modified_attrs.get("movimiento", 50) * penalty_factor)

    return modified_attrs