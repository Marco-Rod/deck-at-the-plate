"""Evaluación batch de MomentContext clasificados como MULTI_HR_GAME."""

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import MomentContext, MomentType
from etl.services.moment_evaluations import detect_moment_type, evaluate_moment


logger = logging.getLogger("etl.services.multi_hr_moment_evaluations")


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
    contexts = (
        db.query(MomentContext)
        .filter(MomentContext.role == "BATTER")
        .order_by(MomentContext.occurred_at.asc(), MomentContext.id.asc())
        .all()
    )
    selected = [
        context
        for context in contexts
        if detect_moment_type(context) == MomentType.MULTI_HR_GAME
    ]
    counts = {key: 0 for key in ("created", "updated", "unchanged", "failed")}
    evaluation_ids = []
    failures = []
    for context in selected:
        try:
            result = evaluate_moment(db, moment_context_id=context.id)
            if result.moment_type != MomentType.MULTI_HR_GAME:
                raise ValueError("evaluate_moment devolvió un tipo inesperado")
            counts[result.status.lower()] += 1
            evaluation_ids.append(result.moment_evaluation_id)
        except Exception as exc:
            db.rollback()
            counts["failed"] += 1
            failures.append(MultiHrMomentEvaluationFailure(context.id, str(exc)))
            logger.exception(
                "multi-HR evaluation failed moment_context_id=%s", context.id
            )
    return MultiHrMomentEvaluationBatchResult(
        selected=len(selected),
        created=counts["created"],
        updated=counts["updated"],
        unchanged=counts["unchanged"],
        failed=counts["failed"],
        moment_evaluation_ids=tuple(evaluation_ids),
        failures=tuple(failures),
    )
