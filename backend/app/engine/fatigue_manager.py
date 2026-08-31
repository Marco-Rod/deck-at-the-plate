import logging
from typing import Dict

logger = logging.getLogger(__name__)

# ⭐ MEJORADO: Umbrales más bajos para fatiga MÁS AGRESIVA
# Estos son los puntos donde comienza la fatiga (threshold)
FATIGUE_THRESHOLDS = {
    3: 6,    # 3 innings: fatiga comienza a los 6 pitches (fin del 1er inning típico)
    6: 15,   # 6 innings: fatiga comienza a los 15 pitches (mitad del 3er inning)
    9: 25,   # 9 innings: fatiga comienza a los 25 pitches (mitad del 5to inning)
}

# ⭐ MEJORADO: Degradación MUCHO MÁS AGRESIVA
# Cada lanzamiento extra = -2% (antes era normalizado, ahora es fijo y severo)
FATIGUE_PENALTY_STEP = 1  # Cada lanzamiento extra después del threshold

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


def compute_fatigue_level(pitch_count: int, total_innings: int = 9) -> float:
    """
    Nivel de fatiga (0-100%) de un pitcher según su conteo de lanzamientos.

    Fórmula (idéntica a la usada en gameplay.py y payloads):
        extra = pitch_count - threshold
        penalty_factor = 1.0 - (0.10 * extra)
        fatigue = (1.0 - penalty_factor) * 100   (cap 0-100)

    Args:
        pitch_count:   Número de lanzamientos realizados.
        total_innings: Duración configurada (3, 6 o 9).

    Returns:
        Porcentaje de fatiga entre 0.0 y 100.0.
    """
    pitch_threshold = get_pitch_threshold(total_innings)

    if pitch_count > pitch_threshold:
        extra_pitches = pitch_count - pitch_threshold
        penalty_factor = 1.0 - (0.10 * extra_pitches)
        return min(100.0, max(0.0, (1.0 - penalty_factor) * 100.0))

    return 0.0


def apply_pitcher_fatigue(
    pitcher_attrs: Dict[str, int], 
    pitch_count: int,
    total_innings: int = 9
) -> Dict[str, int]:
    """
    Aplica penalizaciones AGRESIVAS a Velocidad, Control y Movimiento.
    
    DISEÑO ESTRATÉGICO - Los lanzadores se cansan RÁPIDO:
    
    3 INNINGS:
      - 6 pitches (threshold):   0% fatiga
      - 9 pitches (3 extra):    30% fatiga
      - 12 pitches (6 extra):   60% fatiga 🟠 TIRED
      - 16 pitches (10 extra):  100% fatiga (completely exhausted)
    
    6 INNINGS:
      - 15 pitches (threshold): 0% fatiga
      - 18 pitches (3 extra):   30% fatiga
      - 25 pitches (10 extra):  100% fatiga
    
    9 INNINGS:
      - 25 pitches (threshold): 0% fatiga
      - 30 pitches (5 extra):   50% fatiga
      - 35 pitches (10 extra):  100% fatiga
    
    Fórmula: penalty_factor = 1.0 - (0.10 * extra_pitches)
             Sin cap en penalty_factor, pero estadísticas tienen mínimo de 1
    
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
    
    # ⭐ DEBUG: Log de aplicación de fatiga
    logger.debug(
        "Aplicando fatiga: pitch_count=%s innings=%s threshold=%s excede=%s",
        pitch_count, total_innings, pitch_threshold, pitch_count > pitch_threshold,
    )

    if pitch_count > pitch_threshold:
        extra_pitches = pitch_count - pitch_threshold
        
        # ⭐ AGRESIVO: -10% por cada lanzamiento extra
        # Sin cap en penalty_factor, permite llegar a fatiga 100%
        penalty_factor = 1.0 - (0.10 * extra_pitches)
        
        logger.debug(
            "Fatiga: extra_pitches=%s penalty_factor=%.2f degradacion=%.1f%% stats_orig=(VEL=%s CTR=%s MOV=%s)",
            extra_pitches, penalty_factor, max(0, (1.0 - penalty_factor) * 100.0),
            pitcher_attrs.get("velocidad"), pitcher_attrs.get("control"), pitcher_attrs.get("movimiento"),
        )

        # Aplicar penalización pero asegurar mínimo de 1 en cada stat
        modified_attrs["velocidad"] = max(1, int(modified_attrs.get("velocidad", 50) * penalty_factor))
        modified_attrs["control"] = max(1, int(modified_attrs.get("control", 50) * penalty_factor))
        modified_attrs["movimiento"] = max(1, int(modified_attrs.get("movimiento", 50) * penalty_factor))
        
        logger.debug(
            "Fatiga aplicada: VEL=%s CTR=%s MOV=%s",
            modified_attrs["velocidad"], modified_attrs["control"], modified_attrs["movimiento"],
        )
    else:
        logger.debug("No se aplico fatiga (pitch_count <= threshold)")

    return modified_attrs
