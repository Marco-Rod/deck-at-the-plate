"""Perfiles lingüísticos de nombres GAME (plan V2.1 §64).

El clasificador asigna un perfil por señales deterministas; el generador usa el
pool del perfil. Los perfiles neutrales (UNKNOWN, MULTI_ORIGIN, GENERIC_LATIN)
comparten el pool multiorigen.
"""

from dataclasses import dataclass


# Perfil -> pool de recursos (espejo de resources/names/profiles.yaml).
NAME_PROFILE_POOLS: dict[str, str] = {
    "JAPANESE": "japanese",
    "KOREAN": "korean",
    "CHINESE": "chinese",
    "SPANISH": "spanish",
    "ENGLISH": "english",
    "FRENCH": "french",
    "DUTCH": "dutch",
    "GERMANIC": "germanic",
    "SLAVIC": "slavic",
    "MULTI_ORIGIN": "generic_latin",
    "GENERIC_LATIN": "generic_latin",
    "UNKNOWN": "generic_latin",
}

VALID_PROFILES = frozenset(NAME_PROFILE_POOLS)

# Perfiles que no representan un origen concreto; usan el pool neutral.
NEUTRAL_PROFILES = frozenset({"UNKNOWN", "MULTI_ORIGIN", "GENERIC_LATIN"})


@dataclass(frozen=True)
class NameGenerationProfile:
    """Perfil de generación (§68): origen + buckets aproximados de longitud."""

    name: str
    given_length: str = "MEDIUM"   # SHORT / MEDIUM / LONG
    family_length: str = "MEDIUM"
    components: int = 2            # given + family


def profile_for(pool_hint: str) -> str:
    """Resuelve un perfil válido o cae en UNKNOWN."""
    hint = pool_hint.upper()
    return hint if hint in VALID_PROFILES else "UNKNOWN"