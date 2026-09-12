"""Política de rareza coleccionable por edición, separada del tier de perf.

Semánticas distintas con los mismos tokens hoy:

    PerformanceTier      -> posición del rendimiento frente a la población.
    CollectibleRarity    -> rareza de la carta dentro de esta edición.

La edición declara rarity_policy_version (NULL = ruta legacy). Declarada, la
publicación resuelve obligatoriamente: si no existe la política o no puede
calcularse el tier, se produce un error de publicación, nunca COMMON silencioso.
"""

from typing import Protocol

from app.models import CardEdition, CardRarity
from etl.services.performance_tier2 import (
    PerformanceTierResult,
    calculate_performance_tier,
)
from etl.config.performance_tier_2 import PERFORMANCE_TIER_MODEL_VERSION


RARITY_POLICY_VERSION = "rarity-policy-2.0"

# V1: identidad. La decisión es separar capas (ratings / tier / rarity), no
# todavía redistribuir rareza por economía. El mapping puede evolucionar sin
# tocar ratings.
_IDENTITY_TIER_TO_RARITY = {
    CardRarity.COMMON: CardRarity.COMMON,
    CardRarity.BRONZE: CardRarity.BRONZE,
    CardRarity.SILVER: CardRarity.SILVER,
    CardRarity.GOLD: CardRarity.GOLD,
    CardRarity.DIAMOND: CardRarity.DIAMOND,
}


class RarityPolicy(Protocol):
    version: str

    def resolve(
        self,
        *,
        edition: CardEdition,
        final_overall: int,
        performance_tier: CardRarity,
    ) -> CardRarity: ...


class IdentityRarityPolicy:
    version: str = RARITY_POLICY_VERSION

    def resolve(
        self,
        *,
        edition: CardEdition,
        final_overall: int,
        performance_tier: CardRarity,
    ) -> CardRarity:
        rarity = _IDENTITY_TIER_TO_RARITY.get(performance_tier)
        if rarity is None:
            raise ValueError(f"tier inesperado para la política: {performance_tier}")
        return rarity


RARITY_POLICIES: dict[str, RarityPolicy] = {
    RARITY_POLICY_VERSION: IdentityRarityPolicy(),
}


def resolve_card_rarity(
    edition: CardEdition,
    *,
    final_overall: int,
    performance_tier: CardRarity,
) -> CardRarity:
    """Resuelve la rareza declarada sin fallback; política desconocida falla."""
    if edition.rarity_policy_version is None:
        raise TypeError("rarity_policy_version no declarada; usar ruta legacy")
    policy = RARITY_POLICIES.get(edition.rarity_policy_version)
    if policy is None:
        raise ValueError(
            f"sin política de rareza para {edition.rarity_policy_version}"
        )
    return policy.resolve(
        edition=edition,
        final_overall=final_overall,
        performance_tier=performance_tier,
    )


def final_performance_tier(
    overall_rating: int, rating_distribution
) -> PerformanceTierResult:
    """Tier sobre el OVR final publicado.

    MOMENT puede llevar el OVR final fuera del rango poblacional (ajustes que
    superan el tope del ratings-2.0). Valor por encima del máximo -> percentil
    1.0 (DIAMOND); por debajo del mínimo -> 0.0 (COMMON). El tier nativo
    sigue rechazando valores ajenos al histograma.
    """
    if isinstance(overall_rating, bool) or not isinstance(overall_rating, int):
        raise TypeError("overall_rating debe ser entero")
    if not 40 <= overall_rating <= 99:
        raise ValueError("overall_rating debe estar entre 40 y 99")
    histogram = {
        int(value): int(count)
        for value, count in (rating_distribution.population_histogram or {}).items()
    }
    if not histogram:
        raise ValueError("población vacía; no se puede resolver el tier final")
    if any(count <= 0 for count in histogram.values()):
        raise ValueError("population_histogram contiene conteos inválidos")
    if overall_rating > max(histogram):
        return PerformanceTierResult(
            overall_rating=overall_rating,
            performance_percentile=1.0,
            performance_tier=CardRarity.DIAMOND,
            performance_tier_model_version=PERFORMANCE_TIER_MODEL_VERSION,
        )
    if overall_rating < min(histogram):
        return PerformanceTierResult(
            overall_rating=overall_rating,
            performance_percentile=0.0,
            performance_tier=CardRarity.COMMON,
            performance_tier_model_version=PERFORMANCE_TIER_MODEL_VERSION,
        )
    return calculate_performance_tier(overall_rating, rating_distribution)