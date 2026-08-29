import random
from typing import Any, Dict

from app.core.enums import Difficulty, PitchType, SwingType
from app.core.engine_types import PitchSelection, SwingSelection

# Tipos de picheo que deben coincidir con los usados en el repertorio de las cartas (seed data)
# Orden de definición de PitchType: 4-SEAM, SLIDER, CHANGE, CURVE, SINKER, CUTTER, IBB
_PITCH_TYPES = [p for p in PitchType if p is not PitchType.IBB]


def get_cpu_pitch_action(difficulty: str = "MEDIUM") -> PitchSelection:
    """Genera la selección de picheo de la CPU según la dificultad."""
    if difficulty == Difficulty.HARD:
        zone = random.choice([1, 3, 7, 9])  # Esquinas de la zona
    elif difficulty == Difficulty.EASY:
        zone = random.choice([2, 4, 5, 6, 8])  # Centro y bordes fáciles
    else:
        zone = random.randint(1, 9)

    return {
        "pitch_type": random.choice(_PITCH_TYPES),
        "zone": zone,
    }


def get_cpu_swing_action(difficulty: str = "MEDIUM") -> SwingSelection:
    """Genera la decisión de swing y adivinanza de la CPU."""
    if difficulty == Difficulty.HARD:
        swing_types = [SwingType.NORMAL, SwingType.POWER]
        guess_zone_prob = 0.6
        guess_pitch_prob = 0.5
    else:
        swing_types = [SwingType.NORMAL, SwingType.NORMAL, SwingType.POWER, SwingType.TAKE]
        guess_zone_prob = 0.3
        guess_pitch_prob = 0.2

    return {
        "swing_type": random.choice(swing_types),
        "guessed_zone": random.randint(1, 9) if random.random() < guess_zone_prob else None,
        "guessed_pitch": random.choice(_PITCH_TYPES) if random.random() < guess_pitch_prob else None,
    }


# ---------------------------------------------------------------------------
# CPU Pitcher Change Decision
# ---------------------------------------------------------------------------

# Mínimo de lanzamientos antes de que la CPU pueda considerar un cambio
_CPU_MIN_PITCHES_TO_CHANGE = 5

# Umbrales de fatiga (%) por dificultad a partir de los cuales la CPU decide cambiar
_CPU_CHANGE_FATIGUE_THRESHOLD: Dict[Difficulty, float] = {
    Difficulty.EASY: 95.0,    # Aguanta hasta casi colapsar
    Difficulty.MEDIUM: 65.0,  # Cambia cuando el pitcher está bastante cansado
    Difficulty.HARD: 40.0,    # Cambia proactivamente antes de que el daño sea grave
}

# Probabilidad adicional de cambiar cuando se supera el umbral (agrega variabilidad)
_CPU_CHANGE_PROBABILITY: Dict[Difficulty, float] = {
    Difficulty.EASY: 0.50,    # 50% de decisión de cambiar al superar el umbral
    Difficulty.MEDIUM: 0.75,
    Difficulty.HARD: 0.90,
}


def get_cpu_pitcher_change_decision(
    pitch_count: int,
    fatigue_level: float,
    difficulty: str = "MEDIUM",
) -> bool:
    """
    Decide si la CPU debe cambiar a su pitcher en este momento.

    Lógica:
      1. El pitcher debe haber lanzado al menos _CPU_MIN_PITCHES_TO_CHANGE.
      2. La fatiga debe superar el umbral configurado por dificultad.
      3. Aplica probabilidad aleatoria para añadir variabilidad (la CPU no es perfecta).

    Args:
        pitch_count:   Número de lanzamientos del pitcher activo en este partido.
        fatigue_level: Nivel de fatiga del pitcher (0.0 – 100.0).
        difficulty:    "EASY" | "MEDIUM" | "HARD".

    Returns:
        True si la CPU debe ejecutar un cambio de pitcher, False en caso contrario.
    """
    if pitch_count < _CPU_MIN_PITCHES_TO_CHANGE:
        return False

    threshold = _CPU_CHANGE_FATIGUE_THRESHOLD.get(difficulty, 65.0)
    if fatigue_level < threshold:
        return False

    change_prob = _CPU_CHANGE_PROBABILITY.get(difficulty, 0.75)
    decision = random.random() < change_prob

    print(
        f"🤖 [CPU PITCHER CHANGE DECISION] "
        f"pitches={pitch_count}, fatigue={fatigue_level:.1f}%, "
        f"threshold={threshold}%, prob={change_prob:.0%} → {'CHANGE' if decision else 'KEEP'}"
    )
    return decision


def is_cpu_turn(game, state: Dict[str, Any], required_role: str) -> bool:
    """
    Determina si en este momento le toca actuar a la CPU (PvE).

    En modo PvE:
      - Si CPU es AWAY: Alta → CPU pichea, humano batea. Baja → humano pichea, CPU batea.
      - Si CPU es HOME: Alta → CPU pichea, humano batea. Baja → humano pichea, CPU batea.

    Args:
        game:          Instancia con home_user_id / away_user_id / is_top_inning.
        state:         state_data (mode, is_game_over).
        required_role: 'PITCHER' o 'BATTER' — el rol que se está evaluando.
    """
    mode_check = state.get("mode") != "PVE"
    game_over_check = state.get("is_game_over")

    if mode_check or game_over_check:
        print(f"🤖 is_cpu_turn({required_role}): EARLY EXIT - mode={state.get('mode')}, is_game_over={game_over_check}")
        return False

    # ARREGLADO: Identificar dónde está la CPU
    is_cpu_home = game.home_user_id == "CPU_BOT"
    is_cpu_away = game.away_user_id == "CPU_BOT"

    print(f"🤖 is_cpu_turn({required_role}): is_cpu_home={is_cpu_home}, is_cpu_away={is_cpu_away}, is_top={game.is_top_inning}")

    if not (is_cpu_home or is_cpu_away):
        print(f"🤖 is_cpu_turn({required_role}): No CPU found")
        return False  # No hay CPU en este juego

    if required_role == "PITCHER":
        # CPU pichea en la Alta si es local, o en la Baja si es visitante
        if is_cpu_home:
            result = game.is_top_inning      # CPU local pichea en Alta
            print(f"🤖 is_cpu_turn(PITCHER): CPU es HOME, returning {result}")
            return result
        else:
            result = not game.is_top_inning  # CPU visitante pichea en Baja
            print(f"🤖 is_cpu_turn(PITCHER): CPU es AWAY, returning {result}")
            return result

    if required_role == "BATTER":
        # CPU batea en la Alta si es visitante, o en la Baja si es local
        if is_cpu_away:
            result = game.is_top_inning      # CPU visitante batea en Alta
            print(f"🤖 is_cpu_turn(BATTER): CPU es AWAY, returning {result}")
            return result
        else:
            result = not game.is_top_inning  # CPU local batea en Baja
            print(f"🤖 is_cpu_turn(BATTER): CPU es HOME, returning {result}")
            return result

    return False


def choose_pitch_from_repertoire(repertoire) -> "str | None":
    """
    Selecciona un pitch_type aleatorio del repertorio real de un pitcher.
    Retorna None si el repertorio está vacío o ausente.
    """
    if not repertoire:
        return None
    available_types = [p["pitch_type"] for p in repertoire]
    if not available_types:
        return None
    return random.choice(available_types)