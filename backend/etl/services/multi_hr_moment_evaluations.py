"""Adaptador de evaluación batch para MULTI_HR_GAME."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import MomentType
from etl.services.moment_evaluation_pipeline import evaluate_moment_contexts


@dataclass(frozen=True)
class MultiHrMomentEvaluationFailure:
    moment_context_id: str
    reason: str


@dataclass(frozen=True)
class MultiHrMomentEvaluationBatchResult:
    selected: int
    created: int
    updated: int
    unchanged: int
    failed: int
    moment_evaluation_ids: tuple[str, ...]
    failures: tuple[MultiHrMomentEvaluationFailure, ...]


def evaluate_discovered_multi_hr_moments(
    db: Session,
) -> MultiHrMomentEvaluationBatchResult:
    """Evalúa todos los MULTI_HR_GAME conocidos, aislando fallos por contexto."""
    result = evaluate_moment_contexts(
        db, moment_type=MomentType.MULTI_HR_GAME
    )
    return MultiHrMomentEvaluationBatchResult(
        selected=result.selected,
        created=result.created,
        updated=result.updated,
        unchanged=result.unchanged,
        failed=result.failed,
        moment_evaluation_ids=result.moment_evaluation_ids,
        failures=tuple(
            MultiHrMomentEvaluationFailure(
                failure.moment_context_id, failure.reason
            )
            for failure in result.failures
        ),
    )
