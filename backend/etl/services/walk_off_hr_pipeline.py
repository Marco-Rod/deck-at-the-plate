"""Orquesta el vertical slice WALK_OFF_HR sin duplicar lógica de dominio."""

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import MomentEvaluation, PlayerRatings
from etl.config.league_distributions import DISTRIBUTION_MODEL_VERSION
from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.moment_card_profiles import generate_moment_card_rating_profile
from etl.services.moment_evaluations import evaluate_moment
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
    failed: int
    failures: tuple[WalkOffHrPipelineFailure, ...]


def _source_player_ratings(
    db: Session,
    *,
    player_id: str,
    season: int,
    data_start_date: date,
    data_end_date: date,
    rating_model_version: str,
    distribution_version: str,
) -> PlayerRatings:
    ratings = (
        db.query(PlayerRatings)
        .filter_by(
            player_id=player_id,
            season=season,
            role="BATTER",
            rating_model_version=rating_model_version,
            distribution_version=distribution_version,
            data_start_date=data_start_date,
            data_end_date=data_end_date,
        )
        .one_or_none()
    )
    if ratings is None:
        raise ValueError(
            "PlayerRatings BATTER inexistente para el jugador, versiones y ventana"
        )
    return ratings


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
            context = evaluation.moment_context
            ratings = _source_player_ratings(
                db,
                player_id=context.player_id,
                season=context.season,
                data_start_date=date_from,
                data_end_date=date_to,
                rating_model_version=rating_model_version,
                distribution_version=distribution_version,
            )
            profile_result = generate_moment_card_rating_profile(
                db,
                moment_evaluation_id=evaluation.id,
                source_player_ratings_id=ratings.id,
            )
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
        failed=len(failures),
        failures=tuple(failures),
    )
