"""Overall de carta se deriva de sus atributos finales y es versionado."""

from decimal import Decimal

import pytest

from etl.services.card_overall import (
    CARD_OVERALL_POLICY_VERSION,
    calculate_card_overall,
)


def test_batter_usa_pesos_30_30_25_15_y_round_half_up():
    result = calculate_card_overall(
        role="BATTER",
        final_ratings={
            "contact_rating": 75,
            "power_rating": 82,
            "vision_rating": 70,
            "clutch_rating": 85,
            "overall_rating": 40,
        },
    )
    assert result.raw_score == Decimal("77.35")
    assert result.rating == 77
    assert result.weights == {
        "contact_rating": Decimal("0.30"),
        "power_rating": Decimal("0.30"),
        "vision_rating": Decimal("0.25"),
        "clutch_rating": Decimal("0.15"),
    }
    assert result.policy_version == CARD_OVERALL_POLICY_VERSION
    assert result.source == "FINAL_CARD_RATINGS"


def test_pitcher_usa_pesos_20_30_25_25():
    result = calculate_card_overall(
        role="PITCHER",
        final_ratings={
            "velocity_rating": 71,
            "control_rating": 71,
            "movement_rating": 77,
            "stuff_rating": 79,
        },
    )
    assert result.raw_score == Decimal("74.50")
    assert result.rating == 75


def test_ignora_overall_fuente_y_calcula_desde_componentes():
    low_source = calculate_card_overall(
        role="BATTER",
        final_ratings={
            "contact_rating": 80,
            "power_rating": 80,
            "vision_rating": 80,
            "clutch_rating": 80,
            "overall_rating": 40,
        },
    )
    high_source = calculate_card_overall(
        role="BATTER",
        final_ratings={
            "contact_rating": 80,
            "power_rating": 80,
            "vision_rating": 80,
            "clutch_rating": 80,
            "overall_rating": 99,
        },
    )
    assert low_source.rating == high_source.rating == 80


def test_round_half_up_sube_el_empate():
    result = calculate_card_overall(
        role="BATTER",
        final_ratings={
            "contact_rating": 70,
            "power_rating": 70,
            "vision_rating": 70,
            "clutch_rating": 80,
        },
    )
    assert result.raw_score == Decimal("71.50")
    assert result.rating == 72


def test_rechaza_componentes_incompletos_o_fuera_de_rango():
    with pytest.raises(ValueError, match="power_rating"):
        calculate_card_overall(
            role="BATTER",
            final_ratings={
                "contact_rating": 70,
                "power_rating": None,
                "vision_rating": 70,
                "clutch_rating": 70,
            },
        )
    with pytest.raises(ValueError, match="stuff_rating"):
        calculate_card_overall(
            role="PITCHER",
            final_ratings={
                "velocity_rating": 70,
                "control_rating": 70,
                "movement_rating": 70,
                "stuff_rating": 100,
            },
        )
