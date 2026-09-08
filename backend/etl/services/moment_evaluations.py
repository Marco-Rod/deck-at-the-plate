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
class MultiHrGameEvaluationRules:
    evaluation_version: str = "moment-eval-1.0"
    performance_base: Decimal = Decimal("0.62")
    performance_extra_home_run: Decimal = Decimal("0.16")
    performance_non_hr_hit: Decimal = Decimal("0.035")
    performance_rbi_beyond_two: Decimal = Decimal("0.025")
    uncommonness_two_hr: Decimal = Decimal("0.72")
    uncommonness_three_hr: Decimal = Decimal("0.93")
    uncommonness_four_plus_hr: Decimal = Decimal("1.00")
    leverage_base: Decimal = Decimal("0.15")
    leverage_tying_hr: Decimal = Decimal("0.25")
    leverage_go_ahead_hr: Decimal = Decimal("0.30")
    leverage_deficit_reduction: Decimal = Decimal("0.15")
    leverage_close_game: Decimal = Decimal("0.15")
    leverage_late_inning: Decimal = Decimal("0.15")
    leverage_blowout_penalty: Decimal = Decimal("0.25")
    close_game_max_run_difference: int = 2
    blowout_min_run_difference: int = 5
    late_inning_start: int = 7
    significance_performance_weight: Decimal = Decimal("0.45")
    significance_uncommonness_weight: Decimal = Decimal("0.35")
    significance_leverage_weight: Decimal = Decimal("0.20")


MULTI_HR_GAME_RULES = MultiHrGameEvaluationRules()


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


def _rules_payload(rules) -> dict[str, str]:
    return {key: str(value) for key, value in asdict(rules).items()}


def _validate_rules(rules) -> None:
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


def _multi_hr_leverage(
    home_runs: list, rules: MultiHrGameEvaluationRules
) -> Decimal:
    if len(home_runs) < 2:
        raise ValueError("facts.home_runs requiere al menos dos HR confirmados")
    scores = []
    for index, home_run in enumerate(home_runs):
        if not isinstance(home_run, dict):
            raise ValueError(f"facts.home_runs[{index}] debe ser un objeto")
        inning = _integer_fact(home_run, "inning")
        half_inning = home_run.get("half_inning")
        if half_inning not in {"Top", "Bottom"}:
            raise ValueError(
                f"facts.home_runs[{index}].half_inning debe ser Top o Bottom"
            )
        pre_home = _integer_fact(home_run, "pre_home_score")
        pre_away = _integer_fact(home_run, "pre_away_score")
        post_home = _integer_fact(home_run, "post_home_score")
        post_away = _integer_fact(home_run, "post_away_score")
        if half_inning == "Top":
            pre_team, pre_opponent = pre_away, pre_home
            post_team, post_opponent = post_away, post_home
        else:
            pre_team, pre_opponent = pre_home, pre_away
            post_team, post_opponent = post_home, post_away
        if post_team <= pre_team or post_opponent != pre_opponent:
            raise ValueError(f"facts.home_runs[{index}] contiene marcador inválido")

        pre_margin = pre_team - pre_opponent
        post_margin = post_team - post_opponent
        score = rules.leverage_base
        if pre_margin < 0 and post_margin == 0:
            score += rules.leverage_tying_hr
        elif pre_margin <= 0 and post_margin > 0:
            score += rules.leverage_go_ahead_hr
        elif pre_margin < 0 and post_margin > pre_margin:
            score += rules.leverage_deficit_reduction
        if abs(pre_margin) <= rules.close_game_max_run_difference:
            score += rules.leverage_close_game
        if inning >= rules.late_inning_start:
            score += rules.leverage_late_inning
        if abs(pre_margin) >= rules.blowout_min_run_difference:
            score -= rules.leverage_blowout_penalty
        scores.append(_score(score))
    return _score(sum(scores, Decimal("0")) / Decimal(len(scores)))


def _multi_hr_game_scores(
    batting: dict, home_runs: list, rules: MultiHrGameEvaluationRules
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    hits = _integer_fact(batting, "hits")
    home_run_count = _integer_fact(batting, "home_runs")
    runs_batted_in = _integer_fact(batting, "runs_batted_in")
    if home_run_count < 2 or len(home_runs) != home_run_count:
        raise ValueError("batting.home_runs debe coincidir con facts.home_runs")
    if hits < home_run_count:
        raise ValueError("batting.hits no puede ser menor que batting.home_runs")
    performance = _score(
        rules.performance_base
        + Decimal(max(0, home_run_count - 2)) * rules.performance_extra_home_run
        + Decimal(max(0, hits - home_run_count)) * rules.performance_non_hr_hit
        + Decimal(max(0, runs_batted_in - 2))
        * rules.performance_rbi_beyond_two
    )
    if home_run_count == 2:
        uncommonness = rules.uncommonness_two_hr
    elif home_run_count == 3:
        uncommonness = rules.uncommonness_three_hr
    else:
        uncommonness = rules.uncommonness_four_plus_hr
    uncommonness = _score(uncommonness)
    leverage = _multi_hr_leverage(home_runs, rules)
    significance = _score(
        performance * rules.significance_performance_weight
        + uncommonness * rules.significance_uncommonness_weight
        + leverage * rules.significance_leverage_weight
    )
    return significance, performance, leverage, uncommonness


def _input_hash(
    context: MomentContext, moment_type: MomentType, rules_payload: dict
) -> str:
    payload = {
        "moment_context_id": context.id,
        "moment_context_input_hash": context.input_hash,
        "role": context.role,
        "facts": context.facts,
        "moment_type": moment_type.value,
        "rules": rules_payload,
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def detect_moment_type(context: MomentContext) -> MomentType | None:
    """Clasifica un contexto por sus hechos, sin evaluarlo ni persistir nada."""
    if context.role != "BATTER":
        return None
    batting = context.facts.get("batting")
    if not isinstance(batting, dict):
        return None
    walk_off = batting.get("walk_off")
    home_runs = batting.get("home_runs")
    if (
        walk_off is True
        and not isinstance(home_runs, bool)
        and isinstance(home_runs, int)
        and home_runs >= 1
    ):
        return MomentType.WALK_OFF_HR
    home_run_plays = context.facts.get("home_runs")
    if (
        not isinstance(home_runs, bool)
        and isinstance(home_runs, int)
        and home_runs >= 2
        and isinstance(home_run_plays, list)
    ):
        return MomentType.MULTI_HR_GAME
    return None


def evaluate_moment(
    db: Session,
    *,
    moment_context_id: str,
    rules: WalkOffHrEvaluationRules = WALK_OFF_HR_RULES,
    multi_hr_rules: MultiHrGameEvaluationRules = MULTI_HR_GAME_RULES,
) -> MomentEvaluationResult:
    """Interpreta tipos de Moment soportados sin producir ajustes ni ratings."""
    context = db.get(MomentContext, moment_context_id)
    if context is None:
        raise ValueError(f"MomentContext inexistente: {moment_context_id}")
    moment_type = detect_moment_type(context)
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
    home_run_plays = context.facts.get("home_runs")
    if moment_type == MomentType.WALK_OFF_HR:
        active_rules = rules
        _validate_rules(active_rules)
        significance, performance, leverage, uncommonness = _walk_off_hr_scores(
            batting, active_rules
        )
    elif moment_type == MomentType.MULTI_HR_GAME:
        active_rules = multi_hr_rules
        _validate_rules(active_rules)
        significance, performance, leverage, uncommonness = _multi_hr_game_scores(
            batting, home_run_plays, active_rules
        )
    else:
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
    rules_payload = _rules_payload(active_rules)
    input_hash = _input_hash(context, moment_type, rules_payload)
    identity = {
        "moment_context_id": context.id,
        "evaluation_version": active_rules.evaluation_version,
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
        "moment_type": moment_type,
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
