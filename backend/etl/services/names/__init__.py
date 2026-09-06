"""Motor de nombres GAME v2.1 (plan §63-§93)."""

from etl.services.names.classifier import NameProfileClassifier
from etl.services.names.generator import FictionalNameGenerator, GameIdentityName, seed_for
from etl.services.names.pools import NamePool, NamePools
from etl.services.names.profiles import (
    NAME_PROFILE_POOLS,
    NEUTRAL_PROFILES,
    VALID_PROFILES,
    NameGenerationProfile,
    profile_for,
)
from etl.services.names.validator import CollisionValidator, contains_blocked

DEFAULT_POOLS = NamePools()

__all__ = [
    "NameProfileClassifier",
    "FictionalNameGenerator",
    "GameIdentityName",
    "seed_for",
    "CollisionValidator",
    "contains_blocked",
    "NamePools",
    "NamePool",
    "NAME_PROFILE_POOLS",
    "NEUTRAL_PROFILES",
    "VALID_PROFILES",
    "NameGenerationProfile",
    "profile_for",
    "DEFAULT_POOLS",
]