"""Políticas explícitas de ratings según el tipo de CardEdition."""

import pytest

from app.models import CardEditionType
from etl.services.card_rating_policies import (
    BASE_RATING_POLICY_VERSION,
    MOMENT_RATING_POLICY_VERSION,
    apply_card_rating_policy,
)


BATTER = {
    "contact_rating": 56,
    "power_rating": 68,
    "vision_rating": 66,
    "clutch_rating": 70,
    "velocity_rating": None,
    "control_rating": None,
    "movement_rating": None,
    "stuff_rating": None,
    "overall_rating": 64,
}


def test_base_es_identity_copy_y_no_muta_la_entrada():
    source = dict(BATTER)
    result = apply_card_rating_policy(
        edition_type=CardEditionType.BASE,
        role="BATTER",
        base_ratings=source,
    )

    assert result.policy_version == BASE_RATING_POLICY_VERSION
    assert result.transformation == "IDENTITY_COPY"
    assert result.adjustments == {}
    assert result.transformed_ratings == source
    assert result.transformed_ratings is not source


def test_moment_aplica_solo_ajustes_explicitos_y_auditables():
    result = apply_card_rating_policy(
        edition_type=CardEditionType.MOMENT,
        role="BATTER",
        base_ratings=BATTER,
        adjustments={
            "power_rating": 12,
            "clutch_rating": 18,
            "overall_rating": 10,
        },
        reason="Walk-off con dos home runs",
    )

    assert result.policy_version == MOMENT_RATING_POLICY_VERSION
    assert result.transformation == "MOMENT_POLICY"
    assert result.base_ratings["power_rating"] == 68
    assert result.transformed_ratings["power_rating"] == 80
    assert result.transformed_ratings["clutch_rating"] == 88
    assert result.transformed_ratings["overall_rating"] == 74
    assert result.transformed_ratings["contact_rating"] == 56
    assert result.adjustments["power_rating"] == 12
    assert result.reason == "Walk-off con dos home runs"


def test_moment_puede_documentar_copia_sin_inventar_boosts():
    result = apply_card_rating_policy(
        edition_type=CardEditionType.MOMENT,
        role="BATTER",
        base_ratings=BATTER,
        reason="Reglas de Moment pendientes",
    )
    assert result.transformed_ratings == result.base_ratings
    assert result.adjustments == {}
    assert result.transformation == "MOMENT_POLICY"


def test_base_rechaza_boosts():
    with pytest.raises(ValueError, match="IDENTITY_COPY"):
        apply_card_rating_policy(
            edition_type=CardEditionType.BASE,
            role="BATTER",
            base_ratings=BATTER,
            adjustments={"power_rating": 1},
        )


def test_moment_exige_razon():
    with pytest.raises(ValueError, match="razón explícita"):
        apply_card_rating_policy(
            edition_type=CardEditionType.MOMENT,
            role="BATTER",
            base_ratings=BATTER,
            adjustments={"power_rating": 1},
        )


@pytest.mark.parametrize(
    "adjustments, message",
    [
        ({"velocity_rating": 1}, "no aplicables"),
        ({"power_rating": 32}, "fuera de 40..99"),
        ({"power_rating": 1.5}, "debe ser entero"),
    ],
)
def test_moment_rechaza_ajustes_invalidos(adjustments, message):
    with pytest.raises(ValueError, match=message):
        apply_card_rating_policy(
            edition_type=CardEditionType.MOMENT,
            role="BATTER",
            base_ratings=BATTER,
            adjustments=adjustments,
            reason="Prueba",
        )


def test_ediciones_sin_politica_fallan_explicita():
    with pytest.raises(ValueError, match="sin política"):
        apply_card_rating_policy(
            edition_type=CardEditionType.ALL_STAR,
            role="BATTER",
            base_ratings=BATTER,
        )
