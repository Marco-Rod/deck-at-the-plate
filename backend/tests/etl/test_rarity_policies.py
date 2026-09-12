"""Política de rareza: contrato Edition -> RarityPolicy y tier final."""

from types import SimpleNamespace

import pytest

from app.models.card import CardRarity
from etl.services.rarity_policies import (
    RARITY_POLICY_VERSION,
    final_performance_tier,
    resolve_card_rarity,
)


def _edition(rarity_policy_version: str | None):
    return SimpleNamespace(rarity_policy_version=rarity_policy_version)


def _distribution(histogram, population_size=None):
    if population_size is None:
        population_size = sum(histogram.values())
    return SimpleNamespace(
        population_size=population_size, population_histogram=histogram
    )


@pytest.mark.parametrize(
    "tier",
    [
        CardRarity.COMMON,
        CardRarity.BRONZE,
        CardRarity.SILVER,
        CardRarity.GOLD,
        CardRarity.DIAMOND,
    ],
)
def test_rarity_policy_2_0_mappe_identidad_por_tier(tier):
    edition = _edition(RARITY_POLICY_VERSION)

    rarity = resolve_card_rarity(
        edition, final_overall=70, performance_tier=tier
    )

    assert rarity == tier


def test_edicion_sin_politica_rechaza_resolucion():
    with pytest.raises(TypeError, match="ruta legacy"):
        resolve_card_rarity(
            _edition(None), final_overall=70, performance_tier=CardRarity.GOLD
        )


def test_politica_desconocida_falla_sin_caida():
    with pytest.raises(ValueError, match="sin política de rareza"):
        resolve_card_rarity(
            _edition("rarity-policy-9.9"),
            final_overall=70,
            performance_tier=CardRarity.GOLD,
        )


def test_tier_final_en_rango_igual_al_nativo():
    distribution = _distribution({"64": 5, "80": 5})

    result = final_performance_tier(64, distribution)

    assert result.performance_tier == CardRarity.COMMON
    assert result.performance_percentile == pytest.approx(0.25)


def test_tier_final_sobre_maximo_poblacional_es_diamond():
    distribution = _distribution({"64": 5, "80": 5})

    result = final_performance_tier(95, distribution)

    assert result.performance_tier == CardRarity.DIAMOND
    assert result.performance_percentile == pytest.approx(1.0)


def test_tier_final_bajo_minimo_poblacional_es_common():
    distribution = _distribution({"64": 5, "80": 5})

    result = final_performance_tier(40, distribution)

    assert result.performance_tier == CardRarity.COMMON
    assert result.performance_percentile == pytest.approx(0.0)


def test_tier_final_rechaza_poblacion_vacia_o_overall_fuera_de_contrato():
    with pytest.raises(ValueError, match="población vacía"):
        final_performance_tier(70, _distribution({}))
    with pytest.raises(ValueError, match="entre 40 y 99"):
        final_performance_tier(20, _distribution({"64": 5, "80": 5}))