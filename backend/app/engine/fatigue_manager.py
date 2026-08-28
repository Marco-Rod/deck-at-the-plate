from typing import Dict, Any

# Umbrales dinámicos basados en el número de innings
# A menos innings, más rápido se fatiga el pitcher proporcionalmente
FATIGUE_THRESHOLDS = {
    3: 18,   # 3 innings: 18 pitches (60 / 9 * 3)
    6: 40,   # 6 innings: 40 pitches (60 / 9 * 6)
    9: 60,   # 9 innings: 60 pitches (default)
}

FATIGUE_PENALTY_STEP = 15  # Cada 15 lanzamientos extra aplica penalización

def get_pitch_threshold(total_innings: int = 9) -> int:
    """
    Calcula el umbral de fatiga proporcional al número de innings.
    
    Lógica:
    - 3 innings: 18 pitches antes de fatiga (20% del tiempo)
    - 6 innings: 40 pitches antes de fatiga (66% del tiempo)
    - 9 innings: 60 pitches antes de fatiga (100% del tiempo)
    
    Para otros valores, interpola proporcionalmente.
    """
    if total_innings in FATIGUE_THRESHOLDS:
        return FATIGUE_THRESHOLDS[total_innings]
    
    # Interpolación: threshold = (60 / 9) * total_innings
    return max(6, int((60.0 / 9.0) * total_innings))


def apply_pitcher_fatigue(
    pitcher_attrs: Dict[str, int], 
    pitch_count: int,
    total_innings: int = 9
) -> Dict[str, int]:
    """
    Aplica penalizaciones a Velocidad, Control y Movimiento si el pitcher
    ha superado su umbral de lanzamientos en la partida.
    
    El umbral se ajusta dinámicamente según el número de innings:
    - Menos innings = fatiga más rápida (proporcionalmente)
    - Más innings = fatiga más lenta
    
    Args:
        pitcher_attrs: Diccionario con velocidad, control, movimiento
        pitch_count: Número de lanzamientos realizados
        total_innings: Total de innings en la partida (3, 6, o 9)
    
    Returns:
        Diccionario con atributos modificados por fatiga
    """
    modified_attrs = pitcher_attrs.copy()
    
    # Obtener umbral dinámico basado en innings
    pitch_threshold = get_pitch_threshold(total_innings)

    if pitch_count > pitch_threshold:
        extra_pitches = pitch_count - pitch_threshold
        # Penalización: -3% en atributos por cada tramo de 15 picheos extra
        penalty_factor = 1.0 - (0.03 * (extra_pitches // FATIGUE_PENALTY_STEP + 1))
        penalty_factor = max(0.5, penalty_factor)  # Límite máximo de degradación: -50%

        modified_attrs["velocidad"] = int(modified_attrs.get("velocidad", 50) * penalty_factor)
        modified_attrs["control"] = int(modified_attrs.get("control", 50) * penalty_factor)
        modified_attrs["movimiento"] = int(modified_attrs.get("movimiento", 50) * penalty_factor)

    return modified_attrs
