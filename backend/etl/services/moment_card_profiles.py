"""Orquesta MomentEvaluation hasta CardRatingProfile sin duplicar fórmulas."""

from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from app.models import MomentEvaluation, PlayerRatings
from etl.services.card_rating_profiles import (
    CardRatingProfileResult,
    generate_card_rating_profile,
)
from etl.services.moment_rating_adjustments import (
    WALK_OFF_HR_ADJUSTMENT_RULES,
    MomentRatingAdjustments,
    WalkOffHrAdjustmentRules,
    calculate_moment_rating_adjustments,
)


@dataclass(frozen=True)
class MomentCardRatingProfileResult:
    status: str
    card_rating_profile_id: str
    source_player_ratings_id: str
    source_moment_evaluation_id: str
    input_hash: str
    adjustments: MomentRatingAdjustments


def _calculation_metadata(
    evaluation: MomentEvaluation,
    adjustments: MomentRatingAdjustments,
    adjustment_rules: WalkOffHrAdjustmentRules,
) -> dict:
    context = evaluation.moment_context
    return {
        "calculation_chain": [
            "MomentContext",
            "MomentEvaluation",
            "MomentRatingAdjustmentPolicy",
            "MomentPolicy",
            "CardRatingProfile",
        ],
        "moment_context": {
            "id": context.id,
            "input_hash": context.input_hash,
            "context_version": context.context_version,
            "source_type": context.source_type,
            "source_reference": context.source_reference,
            "occurred_at": context.occurred_at,
            "facts": context.facts,
        },
        "moment_evaluation": {
            "id": evaluation.id,
            "input_hash": evaluation.input_hash,
            "evaluation_version": evaluation.evaluation_version,
            "moment_type": evaluation.moment_type,
            "scores": {
                "significance": evaluation.significance_score,
                "performance": evaluation.performance_score,
                "leverage": evaluation.leverage_score,
                "statistical_uncommonness": evaluation.statistical_uncommonness,
            },
            "rules": evaluation.rules_payload,
        },
        "rating_adjustment_policy": {
            "policy_version": adjustments.policy_version,
            "input_hash": adjustments.input_hash,
            "rules": asdict(adjustment_rules),
            "requested_adjustments": adjustments.requested_adjustments,
            "applied_adjustments": adjustments.applied_adjustments,
            "capped_attributes": adjustments.capped_attributes,
            "transformed_ratings": adjustments.transformed_ratings,
        },
    }


def generate_moment_card_rating_profile(
    db: Session,
    *,
    moment_evaluation_id: str,
    source_player_ratings_id: str,
    adjustment_rules: WalkOffHrAdjustmentRules = WALK_OFF_HR_ADJUSTMENT_RULES,
) -> MomentCardRatingProfileResult:
    """Conecta la cadena existente y persiste únicamente su resultado final."""
    evaluation = db.get(MomentEvaluation, moment_evaluation_id)
    if evaluation is None:
        raise ValueError(f"MomentEvaluation inexistente: {moment_evaluation_id}")
    ratings = db.get(PlayerRatings, source_player_ratings_id)
    if ratings is None:
        raise ValueError(f"PlayerRatings inexistente: {source_player_ratings_id}")

    adjustments = calculate_moment_rating_adjustments(
        evaluation, ratings, rules=adjustment_rules
    )
    profile_result: CardRatingProfileResult = generate_card_rating_profile(
        db,
        source_player_ratings_id=ratings.id,
        card_edition_id=evaluation.moment_context.card_edition_id,
        policy_adjustments=adjustments.as_card_policy_adjustments(),
        policy_reason=adjustments.reason,
        calculation_metadata=_calculation_metadata(
            evaluation, adjustments, adjustment_rules
        ),
    )
    return MomentCardRatingProfileResult(
        status=profile_result.status,
        card_rating_profile_id=profile_result.card_rating_profile_id,
        source_player_ratings_id=ratings.id,
        source_moment_evaluation_id=evaluation.id,
        input_hash=profile_result.input_hash,
        adjustments=adjustments,
    )
