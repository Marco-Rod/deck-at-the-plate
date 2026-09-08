"""Adaptador de evaluación batch para 10_STRIKEOUT_GAME."""

from sqlalchemy.orm import Session

from app.models import MomentType
from etl.services.moment_evaluation_pipeline import (
    MomentEvaluationBatchResult,
    evaluate_moment_contexts,
)


def evaluate_discovered_ten_strikeout_moments(
    db: Session,
) -> MomentEvaluationBatchResult:
    """Evalúa todos los 10_STRIKEOUT_GAME mediante el batch común."""
    return evaluate_moment_contexts(
        db, moment_type=MomentType.TEN_STRIKEOUT_GAME
    )
