"""Ajustes puros derivados de MomentEvaluation y PlayerRatings."""

import datetime as dt
from dataclasses import replace
from decimal import Decimal

import pytest

from app.models import MomentContext, MomentEvaluation, MomentType, PlayerRatings
from etl.services.moment_rating_adjustments import (
    MOMENT_RATING_ADJUSTMENT_VERSION,
    WALK_OFF_HR_ADJUSTMENT_RULES,
    calculate_moment_rating_adjustments,
)


def _ratings(**overrides):
    values = {
        "id": "ratings-player-1",
        "player_id": "player-1",
        "season": 2026,
        "role": "BATTER",
        "rating_model_version": "ratings-2.0",
        "distribution_version": "dist-1.0",
        "data_start_date": dt.date(2026, 8, 25),
        "data_end_date": dt.date(2026, 9, 2),
        "contact_rating": 56,
        "power_rating": 68,
        "vision_rating": 66,
        "clutch_rating": 70,
        "overall_rating": 64,
        "input_hash": "r" * 64,
    }
    values.update(overrides)
    return PlayerRatings(**values)


def _evaluation(**overrides):
    context = MomentContext(
        id="context-1",
        player_id="player-1",
        card_edition_id="edition-1",
        role="BATTER",
        season=2026,
        occurred_at=dt.datetime(2026, 9, 5, tzinfo=dt.timezone.utc),
        source_type="STATCAST",
        source_reference="statcast:824230:660271",
        context_version="moment-context-1.0",
        facts={"batting": {"walk_off": True, "home_runs": 2}},
        input_hash="c" * 64,
    )
    values = {
        "id": "evaluation-1",
        "moment_context": context,
        "moment_type": MomentType.WALK_OFF_HR,
        "significance_score": Decimal("0.92000"),
        "performance_score": Decimal("0.84000"),
        "leverage_score": Decimal("1.00000"),
        "statistical_uncommonness": Decimal("0.88000"),
        "evaluation_version": "moment-eval-1.0",
        "rules_payload": {},
        "input_hash": "e" * 64,
    }
    values.update(overrides)
    return MomentEvaluation(**values)


def test_walk_off_hr_produce_ajustes_auditables_sin_mutar_fuentes():
    ratings = _ratings()
    evaluation = _evaluation()
    original = (
        ratings.contact_rating,
        ratings.power_rating,
        ratings.vision_rating,
        ratings.clutch_rating,
    )

    result = calculate_moment_rating_adjustments(evaluation, ratings)

    assert (result.contact, result.power, result.vision, result.clutch) == (6, 13, 3, 16)
    assert result.transformed_ratings == {
        "contact_rating": 62,
        "power_rating": 81,
        "vision_rating": 69,
        "clutch_rating": 86,
    }
    assert result.policy_version == MOMENT_RATING_ADJUSTMENT_VERSION
    assert result.reason == "WALK_OFF_HR"
    assert result.source_moment_evaluation_id == evaluation.id
    assert len(result.input_hash) == 64
    assert original == (
        ratings.contact_rating,
        ratings.power_rating,
        ratings.vision_rating,
        ratings.clutch_rating,
    )


def test_as_card_policy_adjustments_usa_nombres_del_contrato():
    result = calculate_moment_rating_adjustments(_evaluation(), _ratings())
    assert result.as_card_policy_adjustments() == {
        "contact_rating": 6,
        "power_rating": 13,
        "vision_rating": 3,
        "clutch_rating": 16,
    }


def test_mayor_significance_nunca_reduce_un_boost():
    low = calculate_moment_rating_adjustments(
        _evaluation(significance_score=Decimal("0.40")), _ratings()
    )
    high = calculate_moment_rating_adjustments(
        _evaluation(significance_score=Decimal("0.90")), _ratings()
    )
    assert all(
        high.requested_adjustments[field] >= low.requested_adjustments[field]
        for field in high.requested_adjustments
    )


def test_cap_99_reporta_ajustes_realmente_aplicados():
    ratings = _ratings(
        contact_rating=98,
        power_rating=97,
        vision_rating=99,
        clutch_rating=90,
    )
    result = calculate_moment_rating_adjustments(_evaluation(), ratings)

    assert result.transformed_ratings == {
        "contact_rating": 99,
        "power_rating": 99,
        "vision_rating": 99,
        "clutch_rating": 99,
    }
    assert result.applied_adjustments == {
        "contact_rating": 1,
        "power_rating": 2,
        "vision_rating": 0,
        "clutch_rating": 9,
    }
    assert set(result.capped_attributes) == {
        "contact_rating",
        "power_rating",
        "vision_rating",
        "clutch_rating",
    }


def test_cambio_de_version_es_reproducible_y_cambia_fingerprint():
    v1 = calculate_moment_rating_adjustments(_evaluation(), _ratings())
    v2_rules = replace(
        WALK_OFF_HR_ADJUSTMENT_RULES,
        policy_version="moment-rating-adjustment-2.0",
    )
    v2 = calculate_moment_rating_adjustments(
        _evaluation(), _ratings(), rules=v2_rules
    )
    repeated = calculate_moment_rating_adjustments(
        _evaluation(), _ratings(), rules=v2_rules
    )

    assert v1.input_hash != v2.input_hash
    assert v2.input_hash == repeated.input_hash
    assert v2.policy_version == "moment-rating-adjustment-2.0"


def test_rechaza_coeficientes_negativos_que_romperian_monotonicidad():
    invalid_rules = replace(
        WALK_OFF_HR_ADJUSTMENT_RULES,
        contact_significance_weight=Decimal("-1"),
    )
    with pytest.raises(ValueError, match="no negativos"):
        calculate_moment_rating_adjustments(
            _evaluation(), _ratings(), rules=invalid_rules
        )


def test_rechaza_evaluacion_de_otro_jugador():
    with pytest.raises(ValueError, match="mismo jugador/rol"):
        calculate_moment_rating_adjustments(
            _evaluation(), _ratings(player_id="player-2")
        )


def test_rechaza_player_ratings_pitcher():
    with pytest.raises(ValueError, match="BATTER"):
        calculate_moment_rating_adjustments(_evaluation(), _ratings(role="PITCHER"))


def test_no_persiste_ni_agrega_campos_a_los_modelos():
    evaluation_columns = set(MomentEvaluation.__table__.columns.keys())
    ratings_columns = set(PlayerRatings.__table__.columns.keys())
    assert "rating_adjustments" not in evaluation_columns
    assert "moment_adjustments" not in ratings_columns
