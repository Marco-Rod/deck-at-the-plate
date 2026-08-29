import random
from typing import Any, Dict

from app.core.enums import Difficulty, PitchType, SwingType, PlayerRole
from app.core.engine_types import PitchSelection, SwingSelection
from app.engine.game_rules import MIN_PITCHES_TO_CHANGE
from app.engine.turn_guard import expected_actor

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
# (regla compartida con el motor — ver app/engine/game_rules.py)

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
      1. El pitcher debe haber lanzado al menos MIN_PITCHES_TO_CHANGE.
      2. La fatiga debe superar el umbral configurado por dificultad.
      3. Aplica probabilidad aleatoria para añadir variabilidad (la CPU no es perfecta).

    Args:
        pitch_count:   Número de lanzamientos del pitcher activo en este partido.
        fatigue_level: Nivel de fatiga del pitcher (0.0 – 100.0).
        difficulty:    "EASY" | "MEDIUM" | "HARD".

    Returns:
        True si la CPU debe ejecutar un cambio de pitcher, False en caso contrario.
    """
    if pitch_count < MIN_PITCHES_TO_CHANGE:
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

    Reutiliza ``expected_actor`` (turn_guard) como ÚNICA fuente del mapeo
    rol → jugador según la media entrada, evitando duplicar la regla de turno.
    Solo es turno de la CPU en modo PVE con partida activa.

    Args:
        game:          Instancia con home_user_id / away_user_id / is_top_inning.
        state:         state_data (mode, is_game_over).
        required_role: 'PITCHER' o 'BATTER' — el rol que se está evaluando.
    """
    if required_role not in (PlayerRole.PITCHER, PlayerRole.BATTER):
        return False
    if state.get("mode") != "PVE" or state.get("is_game_over"):
        return False
    return expected_actor(game, required_role) == "CPU_BOT"


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