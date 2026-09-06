"""Pruebas de la política pura de pitcher traits 2.0."""

import pytest

from etl.services.pitcher_traits2 import NO_TRAIT, calculate_pitcher_trait


@pytest.mark.parametrize(
    ("ratings", "expected"),
    [
        ((95, 70, 70, 70), "HIGH_HEAT"),
        ((70, 92, 71, 72), "PAINTER"),
        ((70, 72, 90, 73), "BIG_BREAK"),
        ((72, 72, 74, 91), "NASTY"),
        ((80, 79, 78, 77), "COMPLETE_ARM"),
        ((79, 71, 70, 70), NO_TRAIT),
        ((85, 82, 70, 70), NO_TRAIT),
        ((71, 71, 77, 79), NO_TRAIT),
    ],
)
def test_calcula_trait_segun_perfil_normalizado(ratings, expected):
    assert calculate_pitcher_trait(*ratings) == expected


def test_complete_arm_tiene_prioridad_sobre_trait_dominante():
    assert calculate_pitcher_trait(80, 75, 75, 75) == "COMPLETE_ARM"


@pytest.mark.parametrize("ratings", [(-1, 70, 70, 70), (100, 70, 70, 70)])
def test_rechaza_ratings_fuera_de_rango(ratings):
    with pytest.raises(ValueError, match="entre 0 y 99"):
        calculate_pitcher_trait(*ratings)
