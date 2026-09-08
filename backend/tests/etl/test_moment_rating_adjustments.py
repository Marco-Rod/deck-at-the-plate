"""Ajustes puros derivados de MomentEvaluation y PlayerRatings."""

import datetime as dt
from dataclasses import replace
from decimal import Decimal

import pytest

from app.models import MomentContext, MomentEvaluation, MomentType, PlayerRatings
from etl.services.moment_rating_adjustments import (
    MOMENT_RATING_ADJUSTMENT_VERSION,
    MULTI_HR_GAME_ADJUSTMENT_RULES,
    WALK_OFF_HR_ADJUSTMENT_RULES,
    calculate_multi_hr_game_rating_adjustments,
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


def _multi_evaluation(*, performance, uncommonness, leverage, significance):
    return _evaluation(
        moment_type=MomentType.MULTI_HR_GAME,
        performance_score=Decimal(performance),
        statistical_uncommonness=Decimal(uncommonness),
        leverage_score=Decimal(leverage),
        significance_score=Decimal(significance),
    )


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


@pytest.mark.parametrize(
    ("scores", "expected"),
    [
        ((".915", ".930", ".31667", ".80058"), (7, 17, 2, 4)),
        ((".680", ".720", ".650", ".688"), (6, 14, 2, 6)),
        ((".695", ".720", ".050", ".57475"), (6, 14, 2, 2)),
        ((".830", ".930", ".06667", ".71233"), (7, 16, 2, 3)),
    ],
)
def test_multi_hr_reproduce_los_cuatro_controles_reales(scores, expected):
    result = calculate_multi_hr_game_rating_adjustments(
        _multi_evaluation(
            performance=scores[0],
            uncommonness=scores[1],
            leverage=scores[2],
            significance=scores[3],
        ),
        _ratings(),
    )

    assert (result.contact, result.power, result.vision, result.clutch) == expected
    assert result.reason == "MULTI_HR_GAME"
    assert result.policy_version == MOMENT_RATING_ADJUSTMENT_VERSION


def test_multi_hr_cap_distingue_power_solicitado_y_aplicado():
    result = calculate_multi_hr_game_rating_adjustments(
        _multi_evaluation(
            performance=".915",
            uncommonness=".930",
            leverage=".31667",
            significance=".80058",
        ),
        _ratings(power_rating=90),
    )

    assert result.requested_adjustments["power_rating"] == 17
    assert result.transformed_ratings["power_rating"] == 99
    assert result.applied_adjustments["power_rating"] == 9
    assert "power_rating" in result.capped_attributes


def test_multi_hr_es_determinista_y_no_muta_player_ratings():
    ratings = _ratings()
    evaluation = _multi_evaluation(
        performance=".680",
        uncommonness=".720",
        leverage=".650",
        significance=".688",
    )
    original = tuple(getattr(ratings, field) for field in (
        "contact_rating", "power_rating", "vision_rating", "clutch_rating"
    ))

    first = calculate_multi_hr_game_rating_adjustments(evaluation, ratings)
    second = calculate_multi_hr_game_rating_adjustments(evaluation, ratings)

    assert first == second
    assert tuple(getattr(ratings, field) for field in (
        "contact_rating", "power_rating", "vision_rating", "clutch_rating"
    )) == original


def test_multi_hr_power_y_clutch_son_monotonicos():
    base = dict(
        performance=".60",
        uncommonness=".70",
        leverage=".10",
        significance=".60",
    )
    low = calculate_multi_hr_game_rating_adjustments(
        _multi_evaluation(**base), _ratings()
    )
    higher_performance = calculate_multi_hr_game_rating_adjustments(
        _multi_evaluation(**{**base, "performance": ".90"}), _ratings()
    )
    higher_uncommonness = calculate_multi_hr_game_rating_adjustments(
        _multi_evaluation(**{**base, "uncommonness": ".95"}), _ratings()
    )
    higher_leverage = calculate_multi_hr_game_rating_adjustments(
        _multi_evaluation(**{**base, "leverage": ".90"}), _ratings()
    )

    assert higher_performance.power >= low.power
    assert higher_uncommonness.power >= low.power
    assert higher_leverage.clutch >= low.clutch


def test_multi_hr_rechaza_pitcher_y_walk_off():
    multi = _multi_evaluation(
        performance=".68",
        uncommonness=".72",
        leverage=".65",
        significance=".688",
    )
    with pytest.raises(ValueError, match="BATTER"):
        calculate_multi_hr_game_rating_adjustments(
            multi, _ratings(role="PITCHER")
        )
    with pytest.raises(ValueError, match="moment_type no soportado"):
        calculate_multi_hr_game_rating_adjustments(_evaluation(), _ratings())


def test_multi_hr_reglas_forman_parte_del_fingerprint():
    evaluation = _multi_evaluation(
        performance=".68",
        uncommonness=".72",
        leverage=".65",
        significance=".688",
    )
    v1 = calculate_multi_hr_game_rating_adjustments(evaluation, _ratings())
    changed = calculate_multi_hr_game_rating_adjustments(
        evaluation,
        _ratings(),
        rules=replace(
            MULTI_HR_GAME_ADJUSTMENT_RULES,
            power_base=Decimal("6"),
        ),
    )

    assert v1.input_hash != changed.input_hash


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
