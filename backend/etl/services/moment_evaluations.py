"""Evaluación reproducible de momentos; no produce ajustes ni ratings."""

import hashlib
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models import MomentContext, MomentEvaluation, MomentType


SCORE_QUANTUM = Decimal("0.00001")


@dataclass(frozen=True)
class WalkOffHrEvaluationRules:
    evaluation_version: str = "moment-eval-1.0"
    performance_base: Decimal = Decimal("0.60")
    performance_hit_beyond_first: Decimal = Decimal("0.03")
    performance_home_run: Decimal = Decimal("0.05")
    performance_rbi: Decimal = Decimal("0.01")
    uncommonness_base: Decimal = Decimal("0.75")
    uncommonness_extra_home_run: Decimal = Decimal("0.08")
    uncommonness_rbi_beyond_three: Decimal = Decimal("0.025")
    significance_leverage_weight: Decimal = Decimal("0.45")
    significance_performance_weight: Decimal = Decimal("0.35")
    significance_uncommonness_weight: Decimal = Decimal("0.20")


WALK_OFF_HR_RULES = WalkOffHrEvaluationRules()


@dataclass(frozen=True)
class MomentEvaluationResult:
    status: str
    moment_evaluation_id: str | None
    moment_context_id: str
    moment_type: MomentType | None
    significance_score: Decimal | None
    performance_score: Decimal | None
    leverage_score: Decimal | None
    statistical_uncommonness: Decimal | None
    evaluation_version: str
    input_hash: str | None


def _score(value: Decimal) -> Decimal:
    bounded = max(Decimal("0"), min(Decimal("1"), value))
    return bounded.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)


def _rules_payload(rules: WalkOffHrEvaluationRules) -> dict[str, str]:
    return {key: str(value) for key, value in asdict(rules).items()}


def _validate_rules(rules: WalkOffHrEvaluationRules) -> None:
    if not rules.evaluation_version or not rules.evaluation_version.strip():
        raise ValueError("evaluation_version es obligatorio")
    weights = (
        rules.significance_leverage_weight,
        rules.significance_performance_weight,
        rules.significance_uncommonness_weight,
    )
    if any(weight < 0 for weight in weights) or sum(weights) != Decimal("1"):
        raise ValueError("los pesos de significance deben ser no negativos y sumar 1")


def _integer_fact(facts: dict, key: str) -> int:
    value = facts.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"batting.{key} debe ser un entero no negativo")
    return value


def _walk_off_hr_scores(
    batting: dict, rules: WalkOffHrEvaluationRules
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    hits = _integer_fact(batting, "hits")
    home_runs = _integer_fact(batting, "home_runs")
    runs_batted_in = _integer_fact(batting, "runs_batted_in")
    performance = _score(
        rules.performance_base
        + Decimal(max(0, hits - 1)) * rules.performance_hit_beyond_first
        + Decimal(home_runs) * rules.performance_home_run
        + Decimal(runs_batted_in) * rules.performance_rbi
    )
    uncommonness = _score(
        rules.uncommonness_base
        + Decimal(max(0, home_runs - 1)) * rules.uncommonness_extra_home_run
        + Decimal(max(0, runs_batted_in - 3))
        * rules.uncommonness_rbi_beyond_three
    )
    leverage = Decimal("1.00000")
    significance = _score(
        leverage * rules.significance_leverage_weight
        + performance * rules.significance_performance_weight
        + uncommonness * rules.significance_uncommonness_weight
    )
    return significance, performance, leverage, uncommonness


def _input_hash(context: MomentContext, rules_payload: dict) -> str:
    payload = {
        "moment_context_id": context.id,
        "moment_context_input_hash": context.input_hash,
        "role": context.role,
        "facts": context.facts,
        "moment_type": MomentType.WALK_OFF_HR.value,
        "rules": rules_payload,
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def evaluate_moment(
    db: Session,
    *,
    moment_context_id: str,
    rules: WalkOffHrEvaluationRules = WALK_OFF_HR_RULES,
) -> MomentEvaluationResult:
    """Detecta y evalúa WALK_OFF_HR con reglas versionadas, sin tocar ratings."""
    _validate_rules(rules)
    context = db.get(MomentContext, moment_context_id)
    if context is None:
        raise ValueError(f"MomentContext inexistente: {moment_context_id}")
    if context.role != "BATTER":
        return MomentEvaluationResult(
            "SKIPPED_UNSUPPORTED",
            None,
            context.id,
            None,
            None,
            None,
            None,
            None,
            rules.evaluation_version,
            None,
        )
    batting = context.facts.get("batting")
    if not isinstance(batting, dict):
        raise ValueError("MomentContext BATTER requiere facts.batting")
    walk_off = batting.get("walk_off")
    home_runs = batting.get("home_runs")
    is_walk_off_hr = (
        walk_off is True
        and not isinstance(home_runs, bool)
        and isinstance(home_runs, int)
        and home_runs >= 1
    )
    if not is_walk_off_hr:
        return MomentEvaluationResult(
            "SKIPPED_UNSUPPORTED",
            None,
            context.id,
            None,
            None,
            None,
            None,
            None,
            rules.evaluation_version,
            None,
        )
    significance, performance, leverage, uncommonness = _walk_off_hr_scores(
        batting, rules
    )
    rules_payload = _rules_payload(rules)
    input_hash = _input_hash(context, rules_payload)
    identity = {
        "moment_context_id": context.id,
        "evaluation_version": rules.evaluation_version,
    }
    evaluation = db.query(MomentEvaluation).filter_by(**identity).one_or_none()
    if evaluation is not None and evaluation.input_hash == input_hash:
        return MomentEvaluationResult(
            "UNCHANGED",
            evaluation.id,
            context.id,
            evaluation.moment_type,
            evaluation.significance_score,
            evaluation.performance_score,
            evaluation.leverage_score,
            evaluation.statistical_uncommonness,
            evaluation.evaluation_version,
            input_hash,
        )

    values = {
        "moment_type": MomentType.WALK_OFF_HR,
        "significance_score": significance,
        "performance_score": performance,
        "leverage_score": leverage,
        "statistical_uncommonness": uncommonness,
        "rules_payload": rules_payload,
        "input_hash": input_hash,
    }
    if evaluation is None:
        evaluation = MomentEvaluation(**identity, **values)
        db.add(evaluation)
        status = "CREATED"
    else:
        for field_name, value in values.items():
            setattr(evaluation, field_name, value)
        status = "UPDATED"
    db.commit()
    return MomentEvaluationResult(
        status,
        evaluation.id,
        context.id,
        evaluation.moment_type,
        evaluation.significance_score,
        evaluation.performance_score,
        evaluation.leverage_score,
        evaluation.statistical_uncommonness,
        evaluation.evaluation_version,
        input_hash,
    )
