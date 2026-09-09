"""Ajustes puros derivados de MomentEvaluation y PlayerRatings."""

import datetime as dt
from dataclasses import replace
from decimal import Decimal

import pytest

from app.models import MomentContext, MomentEvaluation, MomentType, PlayerRatings
from etl.services.moment_rating_adjustments import (
    MOMENT_RATING_ADJUSTMENT_VERSION,
    MULTI_HR_GAME_ADJUSTMENT_RULES,
    TEN_STRIKEOUT_GAME_ADJUSTMENT_RULES,
    WALK_OFF_HR_ADJUSTMENT_RULES,
    calculate_multi_hr_game_rating_adjustments,
    calculate_moment_rating_adjustments,
    calculate_ten_strikeout_game_rating_adjustments,
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


def _pitcher_ratings(*, velocity, control, movement, stuff, **overrides):
    return _ratings(
        role="PITCHER",
        contact_rating=None,
        power_rating=None,
        vision_rating=None,
        clutch_rating=None,
        velocity_rating=velocity,
        control_rating=control,
        movement_rating=movement,
        stuff_rating=stuff,
        **overrides,
    )


def _ten_k_evaluation(*, performance, uncommonness, significance):
    context = MomentContext(
        id="ten-k-context-1",
        player_id="player-1",
        card_edition_id="edition-1",
        role="PITCHER",
        season=2026,
        occurred_at=dt.datetime(2026, 9, 5, tzinfo=dt.timezone.utc),
        source_type="MLB_STATS_API",
        source_reference="mlb:ten-k",
        context_version="moment-context-1.0",
        facts={"pitching": {"strikeouts": 10}},
        input_hash="t" * 64,
    )
    return MomentEvaluation(
        id="ten-k-evaluation-1",
        moment_context=context,
        moment_type=MomentType.TEN_STRIKEOUT_GAME,
        significance_score=Decimal(significance),
        performance_score=Decimal(performance),
        leverage_score=Decimal("0.50000"),
        statistical_uncommonness=Decimal(uncommonness),
        evaluation_version="moment-eval-1.0",
        rules_payload={},
        input_hash="k" * 64,
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


@pytest.mark.parametrize(
    ("ratings", "scores", "budget", "boosts"),
    [
        ((76, 78, 69, 89), (".91450", "1", ".92370"), 29, (5, 7, 7, 10)),
        ((60, 84, 82, 88), (".77412", ".95", ".82197"), 27, (3, 6, 7, 11)),
        ((51, 81, 79, 54), (".74929", ".80", ".75457"), 26, (4, 6, 7, 9)),
        ((54, 60, 77, 49), (".77337", ".75", ".75152"), 26, (4, 5, 8, 9)),
        ((63, 87, 72, 67), (".73500", ".80", ".74600"), 26, (4, 6, 6, 10)),
        ((86, 55, 78, 70), (".70750", ".70", ".69450"), 25, (4, 4, 7, 10)),
        ((68, 63, 77, 88), (".70273", ".70", ".69164"), 25, (4, 4, 6, 11)),
        ((89, 68, 75, 70), (".59571", ".80", ".66243"), 24, (4, 5, 6, 9)),
        ((48, 79, 81, 83), (".62250", ".70", ".64350"), 24, (3, 5, 6, 10)),
    ],
)
def test_ten_k_reproduce_nueve_casos_reales(ratings, scores, budget, boosts):
    result = calculate_ten_strikeout_game_rating_adjustments(
        _ten_k_evaluation(
            performance=scores[0], uncommonness=scores[1], significance=scores[2]
        ),
        _pitcher_ratings(
            velocity=ratings[0],
            control=ratings[1],
            movement=ratings[2],
            stuff=ratings[3],
        ),
    )

    assert result.boost_budget == budget
    assert (result.velocity, result.control, result.movement, result.stuff) == boosts
    assert sum(result.applied_adjustments.values()) == budget


def test_ten_k_gavin_redistribuye_cap_y_conserva_budget():
    result = calculate_ten_strikeout_game_rating_adjustments(
        _ten_k_evaluation(
            performance=".91450", uncommonness="1", significance=".92370"
        ),
        _pitcher_ratings(velocity=76, control=78, movement=69, stuff=89),
    )

    assert result.requested_adjustments == {
        "velocity_rating": 4,
        "control_rating": 6,
        "movement_rating": 7,
        "stuff_rating": 12,
    }
    assert result.applied_adjustments == {
        "velocity_rating": 5,
        "control_rating": 7,
        "movement_rating": 7,
        "stuff_rating": 10,
    }
    assert result.transformed_ratings == {
        "velocity_rating": 81,
        "control_rating": 85,
        "movement_rating": 76,
        "stuff_rating": 99,
    }
    assert result.capped_attributes == ("stuff_rating",)


def test_ten_k_reporta_budget_no_aplicado_si_todo_esta_en_cap():
    result = calculate_ten_strikeout_game_rating_adjustments(
        _ten_k_evaluation(performance="1", uncommonness="1", significance="1"),
        _pitcher_ratings(velocity=99, control=99, movement=99, stuff=99),
    )

    assert sum(result.applied_adjustments.values()) == 0
    assert sum(result.requested_adjustments.values()) == result.boost_budget
    assert set(result.capped_attributes) == set(result.requested_adjustments)


def test_ten_k_es_determinista_no_muta_fuentes_y_versiona_reglas():
    ratings = _pitcher_ratings(velocity=51, control=81, movement=79, stuff=54)
    evaluation = _ten_k_evaluation(
        performance=".74929", uncommonness=".80", significance=".75457"
    )
    original = tuple(getattr(ratings, field) for field in (
        "velocity_rating",
        "control_rating",
        "movement_rating",
        "stuff_rating",
    ))

    first = calculate_ten_strikeout_game_rating_adjustments(evaluation, ratings)
    repeated = calculate_ten_strikeout_game_rating_adjustments(evaluation, ratings)
    changed = calculate_ten_strikeout_game_rating_adjustments(
        evaluation,
        ratings,
        rules=replace(
            TEN_STRIKEOUT_GAME_ADJUSTMENT_RULES,
            budget_base=Decimal("13"),
        ),
    )

    assert first == repeated
    assert first.input_hash != changed.input_hash
    assert tuple(getattr(ratings, field) for field in (
        "velocity_rating",
        "control_rating",
        "movement_rating",
        "stuff_rating",
    )) == original


def test_ten_k_rechaza_batter_y_otro_moment_type():
    evaluation = _ten_k_evaluation(
        performance=".75", uncommonness=".80", significance=".76"
    )
    with pytest.raises(ValueError, match="PITCHER"):
        calculate_ten_strikeout_game_rating_adjustments(evaluation, _ratings())
    with pytest.raises(ValueError, match="moment_type no soportado"):
        calculate_ten_strikeout_game_rating_adjustments(
            _evaluation(),
            _pitcher_ratings(velocity=70, control=70, movement=70, stuff=70),
        )


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
