import logging
import math
from typing import Dict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fatigue Policy v2 (GAMEPLAY-ENGINE-001C) — calibrada por Monte Carlo.
#
# Evidencia:
#   001C-1  workload natural ≈ 150 pitches / 9 innings
#   001C-3  BALANCED=100 seleccionada (ventana de decisión progresiva)
#   001C-4  robusta en matchups STRONG/MID/WEAK
#   001C-5  escala proporcional 3/6/9 → 33/67/100
#
# Principio: la fatiga depende del trabajo acumulado respecto al outing, no del
# número de inning. El threshold es ~2/3 del workload natural esperado.
# ---------------------------------------------------------------------------
STANDARD_GAME_INNINGS = 9
STANDARD_PITCH_THRESHOLD = 100  # Juego estándar de 9 innings

# SMOOTH-0.55-F35:
#   w = pitch_count / threshold
#   factor = 1.0                                      si w <= 1
#   factor = FATIGUE_FLOOR + (1 - FATIGUE_FLOOR) * exp(-((w - 1) / FATIGUE_SIGMA) ** 2)
FATIGUE_FLOOR = 0.35
FATIGUE_SIGMA = 0.55


def get_pitch_threshold(total_innings: int = STANDARD_GAME_INNINGS) -> int:
    """
    Umbral de fatiga proporcional a la duración del juego.

    Un juego estándar de 9 innings usa un threshold de 100 lanzamientos
    (~2/3 del workload natural). El resto de duraciones escala desde esa base:

        3 innings -> 33
        6 innings -> 67
        9 innings -> 100

    Pitcher fatigue threshold scales proportionally with game length.
    """
    if total_innings <= 0:
        raise ValueError("total_innings must be positive")

    return max(
        1,
        round(
            STANDARD_PITCH_THRESHOLD
            * total_innings
            / STANDARD_GAME_INNINGS
        ),
    )


def get_fatigue_factor(pitch_count: int, threshold: int) -> float:
    """
    Factor de degradación SMOOTH-0.55-F35 para un workload dado.

    Args:
        pitch_count: lanzamientos acumulados del pitcher.
        threshold:   umbral de fatiga (ver ``get_pitch_threshold``).

    Returns:
        1.0 mientras ``pitch_count <= threshold``; después decae asintóticamente
        hacia ``FATIGUE_FLOOR`` (0.35). Nunca baja del floor.
    """
    if threshold <= 0:
        raise ValueError("threshold must be positive")

    workload = pitch_count / threshold

    if workload <= 1.0:
        return 1.0

    return FATIGUE_FLOOR + (1.0 - FATIGUE_FLOOR) * math.exp(
        -((workload - 1.0) / FATIGUE_SIGMA) ** 2
    )


def compute_fatigue_level(pitch_count: int, total_innings: int = STANDARD_GAME_INNINGS) -> float:
    """
    Nivel de fatiga (0-100%) reportado a UI y usado por la decisión de la CPU.

    Fórmula (LEGACY/APPROX):
        extra = pitch_count - threshold
        penalty_factor = 1.0 - (0.10 * extra)
        fatigue = (1.0 - penalty_factor) * 100   (cap 0-100)

    Desde Fatigue Policy v2 comparte el onset con el motor de resultado
    (``get_pitch_threshold``), pero su magnitud NO es el factor SMOOTH que se
    aplica a los atributos. Deuda registrada: GAMEPLAY-FATIGUE-CPU-001
    (calibrar/reemplazar la semántica de UI/CPU tras 001C-6).

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
    total_innings: int = STANDARD_GAME_INNINGS
) -> Dict[str, int]:
    """
    Aplica la degradación SMOOTH-0.55-F35 a Velocidad, Control y Movimiento.

    Pipeline (Fatigue Policy v2):
        pitch_count
          ↓
        get_pitch_threshold(total_innings)
          ↓
        get_fatigue_factor(pitch_count, threshold)
          ↓
        attr = max(1, int(attr * factor))

    La fatiga emerge del trabajo acumulado, no del inning. El factor nunca baja
    de ``FATIGUE_FLOOR`` (0.35) y cada atributo conserva un mínimo de 1.

    Args:
        pitcher_attrs: Diccionario con velocidad, control, movimiento.
        pitch_count:   Número de lanzamientos realizados.
        total_innings: Total de innings en la partida (3, 6 o 9).

    Returns:
        Diccionario con atributos modificados por fatiga.
    """
    modified_attrs = pitcher_attrs.copy()

    pitch_threshold = get_pitch_threshold(total_innings)
    factor = get_fatigue_factor(pitch_count, pitch_threshold)

    logger.debug(
        "Aplicando fatiga: pitch_count=%s innings=%s threshold=%s factor=%.3f",
        pitch_count, total_innings, pitch_threshold, factor,
    )

    if factor < 1.0:
        modified_attrs["velocidad"] = max(1, int(modified_attrs.get("velocidad", 50) * factor))
        modified_attrs["control"] = max(1, int(modified_attrs.get("control", 50) * factor))
        modified_attrs["movimiento"] = max(1, int(modified_attrs.get("movimiento", 50) * factor))

        logger.debug(
            "Fatiga aplicada: VEL=%s CTR=%s MOV=%s",
            modified_attrs["velocidad"], modified_attrs["control"], modified_attrs["movimiento"],
        )
    else:
        logger.debug("No se aplico fatiga (pitch_count <= threshold)")

    return modified_attrs
