import logging
import math
from typing import Dict, Union

from app.core.enums import FatigueBand
from app.engine.stuff_policy import STUFF_BASELINE, effective_stuff

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


def get_workload(pitch_count: int, threshold: int) -> float:
    """
    Workload estratégico: trabajo acumulado del pitcher relativo a su outing.

    ``workload = pitch_count / threshold``. Es la señal que consume la CPU para
    decidir el cambio (GAMEPLAY-FATIGUE-CPU-001D-2): 1.0 = outing esperado.

    Args:
        pitch_count: lanzamientos acumulados del pitcher.
        threshold:   umbral de fatiga (ver ``get_pitch_threshold``).

    Returns:
        Ratio >= 0.0. Puede superar 1.0 al exceder el umbral del outing.
    """
    if threshold <= 0:
        raise ValueError("threshold must be positive")

    return pitch_count / threshold


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


def get_fatigue_band(factor: float) -> FatigueBand:
    """
    Banda semántica de fatiga para la UI a partir del ``fatigue_factor`` real.

    Cortes (GAMEPLAY-FATIGUE-CPU-001D-5):
        factor >= 0.95           FRESH
        0.80 <= factor < 0.95    TIRING
        0.60 <= factor < 0.80    FATIGUED
        factor < 0.60            EXHAUSTED

    No gobierna la decisión de la CPU; esa usa ``workload`` (ver ``get_workload``).
    """
    if factor >= 0.95:
        return FatigueBand.FRESH
    if factor >= 0.80:
        return FatigueBand.TIRING
    if factor >= 0.60:
        return FatigueBand.FATIGUED
    return FatigueBand.EXHAUSTED


def compute_fatigue_level(pitch_count: int, total_innings: int = STANDARD_GAME_INNINGS) -> float:
    """
    Nivel de fatiga legacy (0-100%) reportado a UI por compatibilidad.

    DEPRECADO (GAMEPLAY-FATIGUE-CPU-001D-2): ya NO es la fuente autoritativa ni
    para UI ni para la CPU. La UI debe preferir ``fatigue_factor``/``fatigue_band``
    y la CPU razona sobre ``get_workload``.

    Fórmula (LEGACY/APPROX):
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
    total_innings: int = STANDARD_GAME_INNINGS
) -> Dict[str, Union[int, float]]:
    """
    Aplica la degradación SMOOTH-0.55-F35 a Velocidad, Control y Movimiento, y la
    política de Stuff (003B-6A) sobre el atributo ``stuff``.

    Pipeline (Fatigue Policy v2 + GAMEPLAY-ENGINE-003B):
        pitch_count
          ↓
        get_pitch_threshold(total_innings)
          ↓
        get_fatigue_factor(pitch_count, threshold)
          ↓
        VEL/CTL/MOV = max(1, int(attr * factor))          # enteros, sin cambio
          ↓
        stuff      = raw * (1 - 0.50 * (1 - factor))     # float, sin truncar

    Stuff entra por la MISMA puerta que la velocidad y el control: este módulo
    es el único que conoce ``fatigue_factor``, y publica un atributo físico ya
    transformado. El calculator recibe el Stuff efectivo y nunca ve la fatiga
    (003B-6A), lo que mantiene la dependencia en una sola dirección.

    Asimetría deliberada entre las dos familias, y NO es un descuido:

        VEL/CTL/MOV  →  ``int()``. Se truncan porque siempre lo hicieron (001C) y
                        su entrada es un entero; el motor los consume enteros.
        stuff       →  float. La política de 003B es multiplicativa PARCIAL y su
                        efecto sobre el poder es de escala pequeña (±7.5 en el
                        rango de carta), así que truncar en esta frontera
                        cuantizaría la señal justo donde es más fina y rompería
                        la reproducción bit-exacta del LAB (contrato S1).

    El Stuff crudo entra por ``pitcher_attrs["stuff"]``. Si el diccionario no lo
    trae (llamadas legacy, o el fallback de una carta sin columna), se asume
    ``STUFF_BASELINE`` (70): Stuff neutro, supresión 0, comportamiento idéntico
    al previo a 003B.

    Args:
        pitcher_attrs: Diccionario con velocidad, control, movimiento y stuff.
        pitch_count:   Número de lanzamientos realizados.
        total_innings: Total de innings en la partida (3, 6 o 9).

    Returns:
        Copia del diccionario con los atributos modificados por fatiga. La
        entrada ``stuff`` es un float; las de velocidad/control/movimiento son
        enteros.
    """
    modified_attrs: Dict[str, Union[int, float]] = pitcher_attrs.copy()

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

    # Stuff (003B-6A). Se calcula SIEMPRE, incluso con factor == 1.0: en fresco
    # la fórmula es exactamente la identidad (1 - 0.50*0 == 1.0), así que no
    # cambia ningún valor, y evitar la rama deja el invariante "stuff siempre
    # presente y float" sin un segundo camino que pueda divergir.
    raw_stuff = modified_attrs.get("stuff", STUFF_BASELINE)
    modified_attrs["stuff"] = effective_stuff(raw_stuff, factor)

    logger.debug(
        "Stuff efectivo: raw=%s factor=%.3f effective=%.3f",
        raw_stuff, factor, modified_attrs["stuff"],
    )

    return modified_attrs
