"""Convierte MomentEvaluation en boosts auditables sin persistir ni mutar ratings."""

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_FLOOR

from app.models import MomentEvaluation, MomentType, PlayerRatings
from etl.services.rating_math import round_rating


MOMENT_RATING_ADJUSTMENT_VERSION = "moment-rating-adjustment-1.0"
BATTER_FIELDS = (
    "contact_rating",
    "power_rating",
    "vision_rating",
    "clutch_rating",
)
PITCHER_FIELDS = (
    "velocity_rating",
    "control_rating",
    "movement_rating",
    "stuff_rating",
)


@dataclass(frozen=True)
class WalkOffHrAdjustmentRules:
    policy_version: str = MOMENT_RATING_ADJUSTMENT_VERSION
    contact_base: Decimal = Decimal("2")
    contact_performance_weight: Decimal = Decimal("3")
    contact_significance_weight: Decimal = Decimal("2")
    power_base: Decimal = Decimal("4")
    power_performance_weight: Decimal = Decimal("5")
    power_uncommonness_weight: Decimal = Decimal("4")
    power_significance_weight: Decimal = Decimal("1")
    vision_significance_weight: Decimal = Decimal("3")
    clutch_base: Decimal = Decimal("5")
    clutch_leverage_weight: Decimal = Decimal("7")
    clutch_significance_weight: Decimal = Decimal("4")


WALK_OFF_HR_ADJUSTMENT_RULES = WalkOffHrAdjustmentRules()


@dataclass(frozen=True)
class MultiHrGameAdjustmentRules:
    policy_version: str = MOMENT_RATING_ADJUSTMENT_VERSION
    contact_base: Decimal = Decimal("2")
    contact_performance_weight: Decimal = Decimal("4")
    contact_significance_weight: Decimal = Decimal("2")
    power_base: Decimal = Decimal("5")
    power_performance_weight: Decimal = Decimal("6")
    power_uncommonness_weight: Decimal = Decimal("5")
    power_significance_weight: Decimal = Decimal("2")
    vision_significance_weight: Decimal = Decimal("3")
    clutch_leverage_weight: Decimal = Decimal("6")
    clutch_significance_weight: Decimal = Decimal("3")


MULTI_HR_GAME_ADJUSTMENT_RULES = MultiHrGameAdjustmentRules()


@dataclass(frozen=True)
class TenStrikeoutGameAdjustmentRules:
    policy_version: str = MOMENT_RATING_ADJUSTMENT_VERSION
    budget_base: Decimal = Decimal("12")
    budget_performance_weight: Decimal = Decimal("8")
    budget_uncommonness_weight: Decimal = Decimal("4")
    budget_significance_weight: Decimal = Decimal("6")
    velocity_weight: Decimal = Decimal("0.15")
    control_weight: Decimal = Decimal("0.20")
    movement_weight: Decimal = Decimal("0.25")
    stuff_weight: Decimal = Decimal("0.40")
    identity_weight: Decimal = Decimal("0.70")
    headroom_weight: Decimal = Decimal("0.30")
    maximum_weight_deviation: Decimal = Decimal("0.25")
    rating_cap: int = 99


TEN_STRIKEOUT_GAME_ADJUSTMENT_RULES = TenStrikeoutGameAdjustmentRules()


@dataclass(frozen=True)
class MomentRatingAdjustments:
    contact: int
    power: int
    vision: int
    clutch: int
    requested_adjustments: dict[str, int]
    applied_adjustments: dict[str, int]
    transformed_ratings: dict[str, int]
    capped_attributes: tuple[str, ...]
    policy_version: str
    reason: str
    source_moment_evaluation_id: str
    source_moment_evaluation_hash: str
    source_player_ratings_id: str
    source_player_ratings_hash: str
    input_hash: str

    def as_card_policy_adjustments(self) -> dict[str, int]:
        """Formato que consume MomentPolicy en la siguiente capa."""
        return dict(self.applied_adjustments)


@dataclass(frozen=True)
class PitcherMomentRatingAdjustments:
    velocity: int
    control: int
    movement: int
    stuff: int
    boost_budget: int
    final_weights: dict[str, Decimal]
    requested_adjustments: dict[str, int]
    applied_adjustments: dict[str, int]
    transformed_ratings: dict[str, int]
    capped_attributes: tuple[str, ...]
    policy_version: str
    reason: str
    source_moment_evaluation_id: str
    source_moment_evaluation_hash: str
    source_player_ratings_id: str
    source_player_ratings_hash: str
    input_hash: str

    def as_card_policy_adjustments(self) -> dict[str, int]:
        return dict(self.applied_adjustments)


def _decimal(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _validate_score(name: str, value) -> Decimal:
    score = _decimal(value)
    if score < 0 or score > 1:
        raise ValueError(f"{name} fuera de rango 0..1")
    return score


def _requested_adjustments(
    evaluation: MomentEvaluation, rules: WalkOffHrAdjustmentRules
) -> dict[str, int]:
    significance = _validate_score(
        "significance_score", evaluation.significance_score
    )
    performance = _validate_score("performance_score", evaluation.performance_score)
    leverage = _validate_score("leverage_score", evaluation.leverage_score)
    uncommonness = _validate_score(
        "statistical_uncommonness", evaluation.statistical_uncommonness
    )
    return {
        "contact_rating": round_rating(
            rules.contact_base
            + performance * rules.contact_performance_weight
            + significance * rules.contact_significance_weight
        ),
        "power_rating": round_rating(
            rules.power_base
            + performance * rules.power_performance_weight
            + uncommonness * rules.power_uncommonness_weight
            + significance * rules.power_significance_weight
        ),
        "vision_rating": round_rating(
            significance * rules.vision_significance_weight
        ),
        "clutch_rating": round_rating(
            rules.clutch_base
            + leverage * rules.clutch_leverage_weight
            + significance * rules.clutch_significance_weight
        ),
    }


def _multi_hr_requested_adjustments(
    evaluation: MomentEvaluation, rules: MultiHrGameAdjustmentRules
) -> dict[str, int]:
    significance = _validate_score(
        "significance_score", evaluation.significance_score
    )
    performance = _validate_score("performance_score", evaluation.performance_score)
    leverage = _validate_score("leverage_score", evaluation.leverage_score)
    uncommonness = _validate_score(
        "statistical_uncommonness", evaluation.statistical_uncommonness
    )
    return {
        "contact_rating": round_rating(
            rules.contact_base
            + performance * rules.contact_performance_weight
            + significance * rules.contact_significance_weight
        ),
        "power_rating": round_rating(
            rules.power_base
            + performance * rules.power_performance_weight
            + uncommonness * rules.power_uncommonness_weight
            + significance * rules.power_significance_weight
        ),
        "vision_rating": round_rating(
            significance * rules.vision_significance_weight
        ),
        "clutch_rating": round_rating(
            leverage * rules.clutch_leverage_weight
            + significance * rules.clutch_significance_weight
        ),
    }


def _rules_payload(rules) -> dict[str, str]:
    return {key: str(value) for key, value in asdict(rules).items()}


def _validate_rules(rules) -> None:
    if not rules.policy_version or not rules.policy_version.strip():
        raise ValueError("policy_version es obligatorio")
    coefficients = (
        value
        for key, value in asdict(rules).items()
        if key != "policy_version"
    )
    if any(value < 0 for value in coefficients):
        raise ValueError("los coeficientes de ajustes deben ser no negativos")


def _input_hash(payload: dict) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bounded_weights(
    base_weights: dict[str, Decimal],
    affinities: dict[str, Decimal],
    deviation: Decimal,
) -> dict[str, Decimal]:
    raw = {field: base_weights[field] * affinities[field] for field in base_weights}
    raw_total = sum(raw.values())
    if raw_total <= 0:
        raise ValueError("las afinidades deben producir peso positivo")
    desired = {field: value / raw_total for field, value in raw.items()}
    lower = {
        field: weight * (Decimal("1") - deviation)
        for field, weight in base_weights.items()
    }
    upper = {
        field: weight * (Decimal("1") + deviation)
        for field, weight in base_weights.items()
    }
    result = {
        field: min(upper[field], max(lower[field], desired[field]))
        for field in desired
    }

    # Proyección determinística al simplex respetando los límites por atributo.
    for _ in range(len(result) * 2):
        difference = Decimal("1") - sum(result.values())
        if abs(difference) < Decimal("0.000000000001"):
            break
        if difference > 0:
            eligible = [field for field in result if result[field] < upper[field]]
            capacity = {field: upper[field] - result[field] for field in eligible}
        else:
            eligible = [field for field in result if result[field] > lower[field]]
            capacity = {field: result[field] - lower[field] for field in eligible}
        if not eligible:
            raise ValueError("los límites de pesos no permiten normalizar a 1")
        basis = {field: raw[field] for field in eligible}
        basis_total = sum(basis.values())
        remaining = abs(difference)
        for field in eligible:
            share = remaining * basis[field] / basis_total
            delta = min(capacity[field], share)
            result[field] += delta if difference > 0 else -delta
    return result


def _allocate_integer_budget(
    budget: int,
    weights: dict[str, Decimal],
    base_ratings: dict[str, int],
    rating_cap: int,
) -> dict[str, int]:
    priority = {
        "stuff_rating": 0,
        "movement_rating": 1,
        "control_rating": 2,
        "velocity_rating": 3,
    }
    quotas = {field: Decimal(budget) * weight for field, weight in weights.items()}
    applied = {
        field: min(
            rating_cap - base_ratings[field],
            int(quota.to_integral_value(rounding=ROUND_FLOOR)),
        )
        for field, quota in quotas.items()
    }
    remaining = budget - sum(applied.values())
    while remaining > 0:
        eligible = [
            field
            for field in applied
            if base_ratings[field] + applied[field] < rating_cap
        ]
        if not eligible:
            break
        field = max(
            eligible,
            key=lambda item: (quotas[item] - applied[item], -priority[item]),
        )
        applied[field] += 1
        remaining -= 1
    return applied


def _calculate_adjustments(
    evaluation: MomentEvaluation,
    player_ratings: PlayerRatings,
    *,
    moment_type: MomentType,
    rules,
    requested_factory,
) -> MomentRatingAdjustments:
    _validate_rules(rules)
    if evaluation.moment_type != moment_type:
        raise ValueError(f"moment_type no soportado: {evaluation.moment_type}")
    if player_ratings.role != "BATTER":
        raise ValueError(f"{moment_type.value} solo soporta PlayerRatings BATTER")
    context = evaluation.moment_context
    if context is None:
        raise ValueError("MomentEvaluation no tiene MomentContext")
    if context.player_id != player_ratings.player_id or context.role != player_ratings.role:
        raise ValueError("MomentEvaluation y PlayerRatings no pertenecen al mismo jugador/rol")
    base_ratings = {field: getattr(player_ratings, field) for field in BATTER_FIELDS}
    if any(
        value is None or isinstance(value, bool) or not isinstance(value, int)
        for value in base_ratings.values()
    ):
        raise ValueError("PlayerRatings BATTER está incompleto")
    requested = requested_factory(evaluation, rules)
    transformed = {}
    applied = {}
    capped = []
    for field in BATTER_FIELDS:
        base = base_ratings[field]
        final = min(99, base + requested[field])
        transformed[field] = final
        applied[field] = final - base
        if applied[field] != requested[field]:
            capped.append(field)

    rules_payload = _rules_payload(rules)
    payload = {
        "policy_version": rules.policy_version,
        "reason": moment_type.value,
        "source_moment_evaluation": {
            "id": evaluation.id,
            "input_hash": evaluation.input_hash,
            "evaluation_version": evaluation.evaluation_version,
            "scores": {
                "significance": str(evaluation.significance_score),
                "performance": str(evaluation.performance_score),
                "leverage": str(evaluation.leverage_score),
                "statistical_uncommonness": str(
                    evaluation.statistical_uncommonness
                ),
            },
        },
        "source_player_ratings": {
            "id": player_ratings.id,
            "input_hash": player_ratings.input_hash,
            "base_ratings": base_ratings,
        },
        "rules": rules_payload,
        "requested_adjustments": requested,
        "applied_adjustments": applied,
        "transformed_ratings": transformed,
        "capped_attributes": capped,
    }
    return MomentRatingAdjustments(
        contact=applied["contact_rating"],
        power=applied["power_rating"],
        vision=applied["vision_rating"],
        clutch=applied["clutch_rating"],
        requested_adjustments=requested,
        applied_adjustments=applied,
        transformed_ratings=transformed,
        capped_attributes=tuple(capped),
        policy_version=rules.policy_version,
        reason=moment_type.value,
        source_moment_evaluation_id=evaluation.id,
        source_moment_evaluation_hash=evaluation.input_hash,
        source_player_ratings_id=player_ratings.id,
        source_player_ratings_hash=player_ratings.input_hash,
        input_hash=_input_hash(payload),
    )


def calculate_moment_rating_adjustments(
    evaluation: MomentEvaluation,
    player_ratings: PlayerRatings,
    *,
    rules: WalkOffHrAdjustmentRules = WALK_OFF_HR_ADJUSTMENT_RULES,
) -> MomentRatingAdjustments:
    """Calcula deltas WALK_OFF_HR; conserva el contrato público original."""
    return _calculate_adjustments(
        evaluation,
        player_ratings,
        moment_type=MomentType.WALK_OFF_HR,
        rules=rules,
        requested_factory=_requested_adjustments,
    )


def calculate_multi_hr_game_rating_adjustments(
    evaluation: MomentEvaluation,
    player_ratings: PlayerRatings,
    *,
    rules: MultiHrGameAdjustmentRules = MULTI_HR_GAME_ADJUSTMENT_RULES,
) -> MomentRatingAdjustments:
    """Calcula boosts Power-oriented para MULTI_HR_GAME sin persistir nada."""
    return _calculate_adjustments(
        evaluation,
        player_ratings,
        moment_type=MomentType.MULTI_HR_GAME,
        rules=rules,
        requested_factory=_multi_hr_requested_adjustments,
    )


def calculate_ten_strikeout_game_rating_adjustments(
    evaluation: MomentEvaluation,
    player_ratings: PlayerRatings,
    *,
    rules: TenStrikeoutGameAdjustmentRules = TEN_STRIKEOUT_GAME_ADJUSTMENT_RULES,
) -> PitcherMomentRatingAdjustments:
    """Distribuye un budget 10-K sobre la identidad D-1 del pitcher."""
    _validate_rules(rules)
    if evaluation.moment_type != MomentType.TEN_STRIKEOUT_GAME:
        raise ValueError(f"moment_type no soportado: {evaluation.moment_type}")
    if player_ratings.role != "PITCHER":
        raise ValueError("10_STRIKEOUT_GAME solo soporta PlayerRatings PITCHER")
    context = evaluation.moment_context
    if context is None:
        raise ValueError("MomentEvaluation no tiene MomentContext")
    if (
        context.player_id != player_ratings.player_id
        or context.role != player_ratings.role
    ):
        raise ValueError(
            "MomentEvaluation y PlayerRatings no pertenecen al mismo jugador/rol"
        )
    base_ratings = {
        field: getattr(player_ratings, field) for field in PITCHER_FIELDS
    }
    if any(
        value is None or isinstance(value, bool) or not isinstance(value, int)
        for value in base_ratings.values()
    ):
        raise ValueError("PlayerRatings PITCHER está incompleto")

    performance = _validate_score(
        "performance_score", evaluation.performance_score
    )
    uncommonness = _validate_score(
        "statistical_uncommonness", evaluation.statistical_uncommonness
    )
    significance = _validate_score(
        "significance_score", evaluation.significance_score
    )
    budget = round_rating(
        rules.budget_base
        + performance * rules.budget_performance_weight
        + uncommonness * rules.budget_uncommonness_weight
        + significance * rules.budget_significance_weight
    )
    base_weights = {
        "velocity_rating": rules.velocity_weight,
        "control_rating": rules.control_weight,
        "movement_rating": rules.movement_weight,
        "stuff_rating": rules.stuff_weight,
    }
    if sum(base_weights.values()) != Decimal("1"):
        raise ValueError("los pesos de personalidad deben sumar 1")
    if rules.identity_weight + rules.headroom_weight != Decimal("1"):
        raise ValueError("los pesos de afinidad deben sumar 1")
    if not Decimal("0") <= rules.maximum_weight_deviation < Decimal("1"):
        raise ValueError("maximum_weight_deviation debe estar en [0, 1)")
    maximum_rating = max(base_ratings.values())
    affinities = {
        field: (
            rules.identity_weight * Decimal(value) / Decimal(maximum_rating)
            + rules.headroom_weight
            * Decimal(rules.rating_cap - value)
            / Decimal(rules.rating_cap)
        )
        for field, value in base_ratings.items()
    }
    final_weights = _bounded_weights(
        base_weights, affinities, rules.maximum_weight_deviation
    )
    requested = _allocate_integer_budget(
        budget,
        final_weights,
        {field: 0 for field in PITCHER_FIELDS},
        budget,
    )
    applied = _allocate_integer_budget(
        budget, final_weights, base_ratings, rules.rating_cap
    )
    transformed = {
        field: base_ratings[field] + applied[field] for field in PITCHER_FIELDS
    }
    capped = tuple(
        field for field in PITCHER_FIELDS if applied[field] < requested[field]
    )
    rules_payload = _rules_payload(rules)
    payload = {
        "policy_version": rules.policy_version,
        "reason": MomentType.TEN_STRIKEOUT_GAME.value,
        "source_moment_evaluation": {
            "id": evaluation.id,
            "input_hash": evaluation.input_hash,
            "evaluation_version": evaluation.evaluation_version,
            "scores": {
                "significance": str(evaluation.significance_score),
                "performance": str(evaluation.performance_score),
                "leverage": str(evaluation.leverage_score),
                "statistical_uncommonness": str(
                    evaluation.statistical_uncommonness
                ),
            },
        },
        "source_player_ratings": {
            "id": player_ratings.id,
            "input_hash": player_ratings.input_hash,
            "base_ratings": base_ratings,
        },
        "rules": rules_payload,
        "boost_budget": budget,
        "final_weights": {key: str(value) for key, value in final_weights.items()},
        "requested_adjustments": requested,
        "applied_adjustments": applied,
        "transformed_ratings": transformed,
        "capped_attributes": capped,
    }
    return PitcherMomentRatingAdjustments(
        velocity=applied["velocity_rating"],
        control=applied["control_rating"],
        movement=applied["movement_rating"],
        stuff=applied["stuff_rating"],
        boost_budget=budget,
        final_weights=final_weights,
        requested_adjustments=requested,
        applied_adjustments=applied,
        transformed_ratings=transformed,
        capped_attributes=capped,
        policy_version=rules.policy_version,
        reason=MomentType.TEN_STRIKEOUT_GAME.value,
        source_moment_evaluation_id=evaluation.id,
        source_moment_evaluation_hash=evaluation.input_hash,
        source_player_ratings_id=player_ratings.id,
        source_player_ratings_hash=player_ratings.input_hash,
        input_hash=_input_hash(payload),
    )
