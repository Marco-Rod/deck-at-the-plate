"""Políticas puras para transformar ratings estadísticos en ratings de carta."""

from dataclasses import dataclass
from typing import Mapping

from app.models import CardEditionType


BASE_RATING_POLICY_VERSION = "base-card-ratings-1.0"
MOMENT_RATING_POLICY_VERSION = "moment-card-ratings-1.0"

BATTER_RATING_FIELDS = (
    "contact_rating",
    "power_rating",
    "vision_rating",
    "clutch_rating",
    "overall_rating",
)
PITCHER_RATING_FIELDS = (
    "velocity_rating",
    "control_rating",
    "movement_rating",
    "stuff_rating",
    "overall_rating",
)
ALL_RATING_FIELDS = frozenset(BATTER_RATING_FIELDS + PITCHER_RATING_FIELDS)


@dataclass(frozen=True)
class CardRatingPolicyResult:
    base_ratings: dict[str, int | None]
    transformed_ratings: dict[str, int | None]
    adjustments: dict[str, int]
    policy_version: str
    reason: str
    transformation: str


def _applicable_fields(role: str) -> tuple[str, ...]:
    if role == "BATTER":
        return BATTER_RATING_FIELDS
    if role == "PITCHER":
        return PITCHER_RATING_FIELDS
    raise ValueError(f"rol no soportado: {role}")


def _validate_base_ratings(
    role: str, base_ratings: Mapping[str, int | None]
) -> dict[str, int | None]:
    unknown = set(base_ratings) - ALL_RATING_FIELDS
    if unknown:
        raise ValueError(f"ratings desconocidos: {sorted(unknown)}")
    applicable = set(_applicable_fields(role))
    normalized = {field: base_ratings.get(field) for field in ALL_RATING_FIELDS}
    for field, value in normalized.items():
        if field in applicable:
            if value is None or isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{field} debe ser un entero para {role}")
            if not 40 <= value <= 99:
                raise ValueError(f"{field} fuera de rango 40..99")
        elif value is not None:
            raise ValueError(f"{field} no aplica al rol {role}")
    return normalized


def _normalize_adjustments(
    role: str, adjustments: Mapping[str, int] | None
) -> dict[str, int]:
    normalized = dict(adjustments or {})
    applicable = set(_applicable_fields(role))
    unknown = set(normalized) - applicable
    if unknown:
        raise ValueError(f"ajustes no aplicables para {role}: {sorted(unknown)}")
    for field, adjustment in normalized.items():
        if isinstance(adjustment, bool) or not isinstance(adjustment, int):
            raise ValueError(f"el ajuste de {field} debe ser entero")
    return normalized


def apply_card_rating_policy(
    *,
    edition_type: CardEditionType,
    role: str,
    base_ratings: Mapping[str, int | None],
    adjustments: Mapping[str, int] | None = None,
    reason: str | None = None,
) -> CardRatingPolicyResult:
    """Aplica una política explícita; no deriva boosts ni recalcula overall."""
    base = _validate_base_ratings(role, base_ratings)
    requested_adjustments = _normalize_adjustments(role, adjustments)

    if edition_type == CardEditionType.BASE:
        if any(requested_adjustments.values()):
            raise ValueError("BASE solo admite IDENTITY_COPY sin ajustes")
        return CardRatingPolicyResult(
            base_ratings=base,
            transformed_ratings=dict(base),
            adjustments={},
            policy_version=BASE_RATING_POLICY_VERSION,
            reason=reason or "BASE_IDENTITY_COPY",
            transformation="IDENTITY_COPY",
        )

    if edition_type == CardEditionType.MOMENT:
        if reason is None or not reason.strip():
            raise ValueError("MOMENT_POLICY requiere una razón explícita")
        transformed = dict(base)
        for field, adjustment in requested_adjustments.items():
            final = transformed[field] + adjustment
            if not 40 <= final <= 99:
                raise ValueError(f"el resultado de {field} queda fuera de 40..99")
            transformed[field] = final
        return CardRatingPolicyResult(
            base_ratings=base,
            transformed_ratings=transformed,
            adjustments=requested_adjustments,
            policy_version=MOMENT_RATING_POLICY_VERSION,
            reason=reason.strip(),
            transformation="MOMENT_POLICY",
        )

    raise ValueError(f"sin política de ratings para edición {edition_type.value}")
