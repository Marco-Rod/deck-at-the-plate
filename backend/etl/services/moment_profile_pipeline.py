"""Operaciones comunes para generar perfiles desde MomentEvaluation."""

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import MomentEvaluation, MomentType
from etl.config.league_distributions import DISTRIBUTION_MODEL_VERSION
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.moment_card_profiles import (
    MomentCardRatingProfileResult,
    generate_moment_card_rating_profile,
)
from etl.services.moment_facts import moment_game_date
from etl.services.moment_rating_adjustments import MomentRatingAdjustments
from etl.services.player_ratings_resolver import resolve_player_ratings_as_of


logger = logging.getLogger("etl.services.moment_profile_pipeline")


@dataclass(frozen=True)
class MomentProfileGenerationResult:
    status: str
    moment_evaluation_id: str
    card_rating_profile_id: str | None
    source_player_ratings_id: str | None
    input_hash: str | None
    adjustments: MomentRatingAdjustments | None


@dataclass(frozen=True)
class MomentProfileBatchFailure:
    moment_evaluation_id: str
    reason: str


@dataclass(frozen=True)
class MomentProfileBatchResult:
    selected: int
    created: int
    updated: int
    unchanged: int
    skipped_no_ratings: int
    failed: int
    card_rating_profile_ids: tuple[str, ...]
    failures: tuple[MomentProfileBatchFailure, ...]


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


def generate_moment_card_profiles(
    db: Session,
    *,
    moment_type: MomentType,
    rating_model_version: str = RATING_MODEL_VERSION,
    distribution_version: str = DISTRIBUTION_MODEL_VERSION,
    moment_evaluation_ids: tuple[str, ...] | None = None,
) -> MomentProfileBatchResult:
    """Procesa todas las evaluaciones de un tipo con aislamiento individual."""
    query = db.query(MomentEvaluation).filter(
        MomentEvaluation.moment_type == moment_type
    )
    if moment_evaluation_ids is not None:
        if not moment_evaluation_ids:
            return MomentProfileBatchResult(0, 0, 0, 0, 0, 0, (), ())
        query = query.filter(MomentEvaluation.id.in_(moment_evaluation_ids))
    evaluations = query.order_by(
        MomentEvaluation.created_at.asc(), MomentEvaluation.id.asc()
    ).all()
    counts = {
        key: 0
        for key in (
            "created",
            "updated",
            "unchanged",
            "skipped_no_ratings",
            "failed",
        )
    }
    profile_ids = []
    failures = []
    for evaluation in evaluations:
        try:
            with db.begin_nested():
                result = generate_profile_for_moment_evaluation(
                    db,
                    evaluation=evaluation,
                    rating_model_version=rating_model_version,
                    distribution_version=distribution_version,
                    commit=False,
                )
            counts[result.status.lower()] += 1
            if result.card_rating_profile_id is not None:
                profile_ids.append(result.card_rating_profile_id)
        except Exception as exc:
            counts["failed"] += 1
            failures.append(MomentProfileBatchFailure(evaluation.id, str(exc)))
            logger.exception(
                "moment profile failed moment_type=%s moment_evaluation_id=%s",
                moment_type.value,
                evaluation.id,
            )
    db.commit()
    return MomentProfileBatchResult(
        selected=len(evaluations),
        created=counts["created"],
        updated=counts["updated"],
        unchanged=counts["unchanged"],
        skipped_no_ratings=counts["skipped_no_ratings"],
        failed=counts["failed"],
        card_rating_profile_ids=tuple(profile_ids),
        failures=tuple(failures),
    )
