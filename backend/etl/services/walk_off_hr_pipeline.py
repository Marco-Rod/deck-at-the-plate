"""Orquesta el vertical slice WALK_OFF_HR sin duplicar lógica de dominio."""

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import MomentEvaluation
from etl.config.league_distributions import DISTRIBUTION_MODEL_VERSION
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.moment_evaluations import evaluate_moment
from etl.services.moment_profile_pipeline import (
    generate_profile_for_moment_evaluation,
)
from etl.services.walk_off_hr_detector import detect_walk_off_home_runs
from etl.sources.mlb import MLBStatsApiClient


logger = logging.getLogger("etl.services.walk_off_hr_pipeline")


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
    counts = {
        "evaluated": 0,
        "evaluations_created": 0,
        "evaluations_updated": 0,
        "evaluations_unchanged": 0,
        "profiles_created": 0,
        "profiles_updated": 0,
        "profiles_unchanged": 0,
        "profiles_skipped_no_ratings": 0,
    }
    failures = [
        WalkOffHrPipelineFailure("DETECTION", None, failure.reason)
        for failure in detection.failures
        if failure.kind == "FAILED"
    ]

    for context_id in detection.moment_context_ids:
        try:
            evaluation_result = evaluate_moment(
                db, moment_context_id=context_id
            )
            if evaluation_result.status == "SKIPPED_UNSUPPORTED":
                raise ValueError("MomentContext no soportado por MomentEvaluator")
            if evaluation_result.moment_evaluation_id is None:
                raise ValueError("MomentEvaluator no produjo MomentEvaluation")
            counts["evaluated"] += 1
            counts[f"evaluations_{evaluation_result.status.lower()}"] += 1

            evaluation = db.get(
                MomentEvaluation, evaluation_result.moment_evaluation_id
            )
            if evaluation is None or evaluation.moment_context is None:
                raise ValueError("MomentEvaluation persistida no tiene contexto")
            profile_result = generate_profile_for_moment_evaluation(
                db,
                evaluation=evaluation,
                rating_model_version=rating_model_version,
                distribution_version=distribution_version,
            )
            if profile_result.status == "SKIPPED_NO_RATINGS":
                counts["profiles_skipped_no_ratings"] += 1
                logger.info(
                    "moment profile skipped: no PlayerRatings as-of "
                    "moment_context_id=%s",
                    evaluation.moment_context_id,
                )
                continue
            counts[f"profiles_{profile_result.status.lower()}"] += 1
        except Exception as exc:
            db.rollback()
            failures.append(
                WalkOffHrPipelineFailure("PROCESSING", context_id, str(exc))
            )
            logger.exception(
                "walk-off pipeline failed moment_context_id=%s", context_id
            )

    return WalkOffHrPipelineResult(
        candidates=detection.selected,
        confirmed=detection.confirmed,
        unconfirmed=detection.unconfirmed,
        contexts_created=detection.created,
        contexts_updated=detection.updated,
        contexts_unchanged=detection.unchanged,
        evaluated=counts["evaluated"],
        evaluations_created=counts["evaluations_created"],
        evaluations_updated=counts["evaluations_updated"],
        evaluations_unchanged=counts["evaluations_unchanged"],
        profiles_created=counts["profiles_created"],
        profiles_updated=counts["profiles_updated"],
        profiles_unchanged=counts["profiles_unchanged"],
        profiles_skipped_no_ratings=counts["profiles_skipped_no_ratings"],
        failed=len(failures),
        failures=tuple(failures),
    )
