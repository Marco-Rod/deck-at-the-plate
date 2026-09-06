"""Pruebas de la política pura de rarity-2.0."""

from types import SimpleNamespace

import pytest

from app.models.card import CardRarity
from etl.services.rarity2 import calculate_rarity, rarity_from_percentile


@pytest.mark.parametrize(
    ("percentile", "expected"),
    [
        (0.0, CardRarity.COMMON),
        (0.399999, CardRarity.COMMON),
        (0.40, CardRarity.BRONZE),
        (0.649999, CardRarity.BRONZE),
        (0.65, CardRarity.SILVER),
        (0.819999, CardRarity.SILVER),
        (0.82, CardRarity.GOLD),
        (0.949999, CardRarity.GOLD),
        (0.95, CardRarity.DIAMOND),
        (1.0, CardRarity.DIAMOND),
    ],
)
def test_boundaries_de_rarity(percentile, expected):
    assert rarity_from_percentile(percentile) == expected


def test_empates_en_maximo_usan_midrank_de_la_poblacion_real():
    histogram = {
        "63": 1, "64": 2, "66": 3, "67": 5, "68": 3, "69": 8,
        "70": 6, "71": 4, "72": 1, "73": 1, "74": 1, "75": 4,
    }
    distribution = SimpleNamespace(population_size=39, population_histogram=histogram)

    result = calculate_rarity(75, distribution)

    assert result.percentile == pytest.approx(37 / 39)
    assert result.rarity == CardRarity.GOLD
    assert result.rarity_model_version == "rarity-2.0"


def test_extremos_unicos_quedan_common_y_diamond():
    distribution = SimpleNamespace(
        population_size=20,
        population_histogram={"60": 1, "70": 18, "90": 1},
    )
    assert calculate_rarity(60, distribution).rarity == CardRarity.COMMON
    assert calculate_rarity(90, distribution).rarity == CardRarity.DIAMOND


def test_rechaza_histograma_inconsistente_o_rating_ajeno():
    invalid = SimpleNamespace(population_size=3, population_histogram={"70": 2})
    with pytest.raises(ValueError, match="population_size"):
        calculate_rarity(70, invalid)
    valid = SimpleNamespace(population_size=2, population_histogram={"70": 2})
    with pytest.raises(ValueError, match="no pertenece"):
        calculate_rarity(71, valid)
