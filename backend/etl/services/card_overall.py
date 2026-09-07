"""Overall jugable derivado exclusivamente de los ratings finales de la carta."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from etl.services.rating_math import round_rating


CARD_OVERALL_POLICY_VERSION = "card-overall-1.0"
CARD_OVERALL_WEIGHTS = {
    "BATTER": {
        "contact_rating": Decimal("0.30"),
        "power_rating": Decimal("0.30"),
        "vision_rating": Decimal("0.25"),
        "clutch_rating": Decimal("0.15"),
    },
    "PITCHER": {
        "velocity_rating": Decimal("0.20"),
        "control_rating": Decimal("0.30"),
        "movement_rating": Decimal("0.25"),
        "stuff_rating": Decimal("0.25"),
    },
}


@dataclass(frozen=True)
class CardOverallPolicyResult:
    rating: int
    raw_score: Decimal
    component_ratings: dict[str, int]
    weights: dict[str, Decimal]
    policy_version: str = CARD_OVERALL_POLICY_VERSION
    source: str = "FINAL_CARD_RATINGS"


def calculate_card_overall(
    *, role: str, final_ratings: Mapping[str, int | None]
) -> CardOverallPolicyResult:
    """Calcula Overall con ROUND_HALF_UP, sin consultar PlayerRatings.overall."""
    weights = CARD_OVERALL_WEIGHTS.get(role)
    if weights is None:
        raise ValueError(f"rol no soportado: {role}")
    components = {}
    for field in weights:
        value = final_ratings.get(field)
        if value is None or isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{field} debe ser un entero para {role}")
        if not 40 <= value <= 99:
            raise ValueError(f"{field} fuera de rango 40..99")
        components[field] = value
    raw_score = sum(
        Decimal(components[field]) * weight for field, weight in weights.items()
    )
    return CardOverallPolicyResult(
        rating=round_rating(raw_score),
        raw_score=raw_score,
        component_ratings=components,
        weights=dict(weights),
    )
