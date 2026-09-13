"""Resolución declarativa de elegibilidad de publicación por CardEdition.

La edición declara la policy exacta. Esta capa materializa su resultado en el
CardRatingProfile; ni los perfiles ni la publicación deben elegir implícitamente
la policy más reciente.
"""

from typing import Protocol

from app.models import CardEdition, CardEditionType, PlayerRatings
from etl.services.base_eligibility_policy import (
    BASE_ELIGIBILITY_POLICY_VERSION,
    assess_base_eligibility,
)


class EligibilityPolicy(Protocol):
    version: str

    def assess(self, *, role: str, player_ratings: PlayerRatings) -> dict: ...


class BaseEligibilityPolicy:
    version = BASE_ELIGIBILITY_POLICY_VERSION

    def assess(self, *, role: str, player_ratings: PlayerRatings) -> dict:
        assessment = assess_base_eligibility(
            role=role,
            player_ratings=player_ratings,
        )
        return {
            "policy_version": assessment.policy_version,
            "status": assessment.decision,
            "reasons": list(assessment.reasons),
        }


ELIGIBILITY_POLICIES: dict[str, EligibilityPolicy] = {
    BASE_ELIGIBILITY_POLICY_VERSION: BaseEligibilityPolicy(),
}


def resolve_materialized_eligibility(
    edition: CardEdition, *, player_ratings: PlayerRatings
) -> dict | None:
    """Devuelve la decisión declarada o ``None`` para una edición legacy.

    Una versión declarada que no exista, o que se asigne a un tipo de edición
    incompatible, es un error explícito. No hay fallback silencioso.
    """
    version = edition.eligibility_policy_version
    if version is None:
        return None
    if edition.edition_type != CardEditionType.BASE:
        raise ValueError(
            "eligibility_policy_version sólo está implementada para edición BASE"
        )
    policy = ELIGIBILITY_POLICIES.get(version)
    if policy is None:
        raise ValueError(f"sin política de elegibilidad para {version}")
    return policy.assess(role=player_ratings.role, player_ratings=player_ratings)
