"""Selección pura de traits de pitcher para ratings-2.0."""

from typing import Final


PITCHER_TRAIT_MODEL_VERSION: Final = "pitcher-traits-2.0"
NO_TRAIT: Final[None] = None

COMPLETE_ARM_MIN_RATING: Final = 75
COMPLETE_ARM_MAX_SPREAD: Final = 8
DOMINANT_TRAIT_MIN_RATING: Final = 80
DOMINANT_TRAIT_MIN_GAP: Final = 5

TRAIT_BY_ATTRIBUTE: Final = {
    "velocity": "HIGH_HEAT",
    "control": "PAINTER",
    "movement": "BIG_BREAK",
    "stuff": "NASTY",
}


def calculate_pitcher_trait(
    velocity: int,
    control: int,
    movement: int,
    stuff: int,
) -> str | None:
    """Devuelve un trait solo cuando el perfil es completo o claramente dominante."""
    ratings = {
        "velocity": velocity,
        "control": control,
        "movement": movement,
        "stuff": stuff,
    }
    if any(isinstance(value, bool) or not isinstance(value, int) for value in ratings.values()):
        raise TypeError("los ratings de pitcher deben ser enteros")
    if any(value < 0 or value > 99 for value in ratings.values()):
        raise ValueError("los ratings de pitcher deben estar entre 0 y 99")

    ordered = sorted(ratings.items(), key=lambda item: item[1], reverse=True)
    best_attribute, best_rating = ordered[0]
    second_rating = ordered[1][1]
    worst_rating = ordered[-1][1]

    if worst_rating >= COMPLETE_ARM_MIN_RATING and best_rating - worst_rating <= COMPLETE_ARM_MAX_SPREAD:
        return "COMPLETE_ARM"
    if best_rating < DOMINANT_TRAIT_MIN_RATING:
        return NO_TRAIT
    if best_rating - second_rating < DOMINANT_TRAIT_MIN_GAP:
        return NO_TRAIT
    return TRAIT_BY_ATTRIBUTE[best_attribute]
