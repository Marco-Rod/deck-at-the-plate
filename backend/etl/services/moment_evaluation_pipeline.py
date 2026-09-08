"""Procesamiento batch común de MomentContext por tipo de momento."""

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import MomentContext, MomentType
from etl.services.moment_evaluations import detect_moment_type, evaluate_moment


logger = logging.getLogger("etl.services.moment_evaluation_pipeline")


@dataclass(frozen=True)
class MomentEvaluationBatchFailure:
    moment_context_id: str
    reason: str


@dataclass(frozen=True)
class MomentEvaluationBatchResult:
    selected: int
    created: int
    updated: int
    unchanged: int
    failed: int
    moment_evaluation_ids: tuple[str, ...]
    failures: tuple[MomentEvaluationBatchFailure, ...]


def evaluate_moment_contexts(
    db: Session,
    *,
    moment_type: MomentType,
) -> MomentEvaluationBatchResult:
    """Evalúa contextos de un tipo con un SAVEPOINT independiente por contexto."""
    contexts = (
        db.query(MomentContext)
        .order_by(MomentContext.occurred_at.asc(), MomentContext.id.asc())
        .all()
    )
    selected = [
        context
        for context in contexts
        if detect_moment_type(context) == moment_type
    ]
    counts = {key: 0 for key in ("created", "updated", "unchanged", "failed")}
    evaluation_ids = []
    failures = []
    for context in selected:
        try:
            with db.begin_nested():
                result = evaluate_moment(
                    db, moment_context_id=context.id, commit=False
                )
                if result.moment_type != moment_type:
                    raise ValueError("evaluate_moment devolvió un tipo inesperado")
                if result.moment_evaluation_id is None:
                    raise ValueError("evaluate_moment no produjo MomentEvaluation")
            counts[result.status.lower()] += 1
            evaluation_ids.append(result.moment_evaluation_id)
        except Exception as exc:
            counts["failed"] += 1
            failures.append(MomentEvaluationBatchFailure(context.id, str(exc)))
            logger.exception(
                "moment evaluation failed moment_type=%s moment_context_id=%s",
                moment_type.value,
                context.id,
            )
    db.commit()
    return MomentEvaluationBatchResult(
        selected=len(selected),
        created=counts["created"],
        updated=counts["updated"],
        unchanged=counts["unchanged"],
        failed=counts["failed"],
        moment_evaluation_ids=tuple(evaluation_ids),
        failures=tuple(failures),
    )
