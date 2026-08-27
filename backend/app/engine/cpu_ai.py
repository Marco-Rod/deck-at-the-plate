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