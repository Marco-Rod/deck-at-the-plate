import random
from typing import Dict, Any

# Tipos de picheo que deben coincidir con los usados en el repertorio de las cartas (seed data)
_PITCH_TYPES = ["4-SEAM", "SLIDER", "CHANGE", "CURVE", "SINKER", "CUTTER"]

def get_cpu_pitch_action(difficulty: str = "MEDIUM") -> Dict[str, Any]:
    """Genera la selección de picheo de la CPU según la dificultad."""
    if difficulty == "HARD":
        zone = random.choice([1, 3, 7, 9])  # Esquinas de la zona
    elif difficulty == "EASY":
        zone = random.choice([2, 4, 5, 6, 8])  # Centro y bordes fáciles
    else:
        zone = random.randint(1, 9)

    return {
        "pitch_type": random.choice(_PITCH_TYPES),
        "zone": zone
    }

def get_cpu_swing_action(difficulty: str = "MEDIUM") -> Dict[str, Any]:
    """Genera la decisión de swing y adivinanza de la CPU."""
    if difficulty == "HARD":
        swing_types = ["NORMAL", "POWER"]
        guess_zone_prob = 0.6
        guess_pitch_prob = 0.5
    else:
        swing_types = ["NORMAL", "NORMAL", "POWER", "TAKE"]
        guess_zone_prob = 0.3
        guess_pitch_prob = 0.2

    return {
        "swing_type": random.choice(swing_types),
        "guessed_zone": random.randint(1, 9) if random.random() < guess_zone_prob else None,
        "guessed_pitch": random.choice(_PITCH_TYPES) if random.random() < guess_pitch_prob else None
    }


# ---------------------------------------------------------------------------
# CPU Pitcher Change Decision
# ---------------------------------------------------------------------------

# Mínimo de lanzamientos antes de que la CPU pueda considerar un cambio
_CPU_MIN_PITCHES_TO_CHANGE = 5

# Umbrales de fatiga (%) por dificultad a partir de los cuales la CPU decide cambiar
_CPU_CHANGE_FATIGUE_THRESHOLD = {
    "EASY":   95.0,  # Aguanta hasta casi colapsar
    "MEDIUM": 65.0,  # Cambia cuando el pitcher está bastante cansado
    "HARD":   40.0,  # Cambia proactivamente antes de que el daño sea grave
}

# Probabilidad adicional de cambiar cuando se supera el umbral (agrega variabilidad)
_CPU_CHANGE_PROBABILITY = {
    "EASY":   0.50,  # 50% de decisión de cambiar al superar el umbral
    "MEDIUM": 0.75,
    "HARD":   0.90,
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
