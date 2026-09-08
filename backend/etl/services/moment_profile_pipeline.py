"""Operación común MomentEvaluation → PlayerRatings D-1 → CardRatingProfile."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import MomentEvaluation
from etl.config.league_distributions import DISTRIBUTION_MODEL_VERSION
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.moment_card_profiles import (
    MomentCardRatingProfileResult,
    generate_moment_card_rating_profile,
)
from etl.services.moment_facts import moment_game_date
from etl.services.moment_rating_adjustments import MomentRatingAdjustments
from etl.services.player_ratings_resolver import resolve_player_ratings_as_of


@dataclass(frozen=True)
class MomentProfileGenerationResult:
    status: str
    moment_evaluation_id: str
    card_rating_profile_id: str | None
    source_player_ratings_id: str | None
    input_hash: str | None
    adjustments: MomentRatingAdjustments | None


def generate_profile_for_moment_evaluation(
    db: Session,
    *,
    evaluation: MomentEvaluation,
    rating_model_version: str = RATING_MODEL_VERSION,
    distribution_version: str = DISTRIBUTION_MODEL_VERSION,
    commit: bool = True,
) -> MomentProfileGenerationResult:
    """Genera un perfil con el snapshot anterior al juego o reporta un skip."""
    if evaluation is None or not evaluation.id:
        raise ValueError("MomentEvaluation persistida es obligatoria")
    context = evaluation.moment_context
    if context is None:
        raise ValueError("MomentEvaluation no tiene MomentContext")
    event_date = moment_game_date(context)
    ratings = resolve_player_ratings_as_of(
        db,
        player_id=context.player_id,
        role=context.role,
        season=context.season,
        as_of_date=event_date,
        rating_model_version=rating_model_version,
        distribution_version=distribution_version,
    )
    if ratings is None:
        return MomentProfileGenerationResult(
            status="SKIPPED_NO_RATINGS",
            moment_evaluation_id=evaluation.id,
            card_rating_profile_id=None,
            source_player_ratings_id=None,
            input_hash=None,
            adjustments=None,
        )

    generated: MomentCardRatingProfileResult = generate_moment_card_rating_profile(
        db,
        moment_evaluation_id=evaluation.id,
        source_player_ratings_id=ratings.id,
        commit=False,
    )
    if commit:
        db.commit()
    else:
        db.flush()
    return MomentProfileGenerationResult(
        status=generated.status,
        moment_evaluation_id=evaluation.id,
        card_rating_profile_id=generated.card_rating_profile_id,
        source_player_ratings_id=ratings.id,
        input_hash=generated.input_hash,
        adjustments=generated.adjustments,
    )
