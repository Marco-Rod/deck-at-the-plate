"""Orquesta el vertical slice WALK_OFF_HR sin duplicar lógica de dominio."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import MomentEvaluation, MomentType
from etl.config.league_distributions import DISTRIBUTION_MODEL_VERSION
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.moment_evaluation_pipeline import evaluate_moment_contexts
from etl.services.moment_profile_pipeline import (
    generate_moment_card_profiles,
)
from etl.services.walk_off_hr_detector import detect_walk_off_home_runs
from etl.sources.mlb import MLBStatsApiClient


@dataclass(frozen=True)
class WalkOffHrPipelineFailure:
    stage: str
    moment_context_id: str | None
    reason: str


@dataclass(frozen=True)
class WalkOffHrPipelineResult:
    candidates: int
    confirmed: int
    unconfirmed: int
    contexts_created: int
    contexts_updated: int
    contexts_unchanged: int
    evaluated: int
    evaluations_created: int
    evaluations_updated: int
    evaluations_unchanged: int
    profiles_created: int
    profiles_updated: int
    profiles_unchanged: int
    profiles_skipped_no_ratings: int
    failed: int
    failures: tuple[WalkOffHrPipelineFailure, ...]


def run_walk_off_hr_pipeline(
    db: Session,
    client: MLBStatsApiClient,
    *,
    date_from: date,
    date_to: date,
    rating_model_version: str = RATING_MODEL_VERSION,
    distribution_version: str = DISTRIBUTION_MODEL_VERSION,
) -> WalkOffHrPipelineResult:
    """Detecta, evalúa y genera perfiles MOMENT mediante servicios existentes."""
    detection = detect_walk_off_home_runs(
        db, client, date_from=date_from, date_to=date_to
    )
    failures = [
        WalkOffHrPipelineFailure("DETECTION", None, failure.reason)
        for failure in detection.failures
        if failure.kind == "FAILED"
    ]
    evaluations = evaluate_moment_contexts(
        db,
        moment_type=MomentType.WALK_OFF_HR,
        moment_context_ids=detection.moment_context_ids,
    )
    failures.extend(
        WalkOffHrPipelineFailure(
            "PROCESSING", failure.moment_context_id, failure.reason
        )
        for failure in evaluations.failures
    )
    profiles = generate_moment_card_profiles(
        db,
        moment_type=MomentType.WALK_OFF_HR,
        rating_model_version=rating_model_version,
        distribution_version=distribution_version,
        moment_evaluation_ids=evaluations.moment_evaluation_ids,
    )
    for failure in profiles.failures:
        evaluation = db.get(MomentEvaluation, failure.moment_evaluation_id)
        failures.append(
            WalkOffHrPipelineFailure(
                "PROCESSING",
                evaluation.moment_context_id if evaluation is not None else None,
                failure.reason,
            )
        )

    return WalkOffHrPipelineResult(
        candidates=detection.selected,
        confirmed=detection.confirmed,
        unconfirmed=detection.unconfirmed,
        contexts_created=detection.created,
        contexts_updated=detection.updated,
        contexts_unchanged=detection.unchanged,
        evaluated=(
            evaluations.created + evaluations.updated + evaluations.unchanged
        ),
        evaluations_created=evaluations.created,
        evaluations_updated=evaluations.updated,
        evaluations_unchanged=evaluations.unchanged,
        profiles_created=profiles.created,
        profiles_updated=profiles.updated,
        profiles_unchanged=profiles.unchanged,
        profiles_skipped_no_ratings=profiles.skipped_no_ratings,
        failed=len(failures),
        failures=tuple(failures),
    )
