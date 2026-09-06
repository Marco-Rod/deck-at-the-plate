"""Tests del clasificador lingüístico (plan V2.1 §84, §86, §87).

Los fixtures prueban cadenas de texto, no atributos personales.
"""

import pytest

from etl.services.names import DEFAULT_POOLS, NameProfileClassifier, VALID_PROFILES


@pytest.fixture(scope="module")
def classifier() -> NameProfileClassifier:
    return NameProfileClassifier(DEFAULT_POOLS)


@pytest.mark.parametrize(
    "first,last,profile",
    [
        ("Haruto", "Yamamoto", "JAPANESE"),
        ("Kenta", "Suzuki", "JAPANESE"),
        ("Shota", "Tanaka", "JAPANESE"),
        ("Minjae", "Kim", "KOREAN"),
        ("Jiho", "Park", "KOREAN"),
        ("Keone", "Jang", "KOREAN"),
        ("Wei", "Wang", "CHINESE"),
        ("Hao", "Li", "CHINESE"),
        ("Jose", "Ramirez", "SPANISH"),
        ("Xavier", "Gonzalez", "SPANISH"),
        ("Ruben", "Hernandez", "SPANISH"),
        ("John", "Smith", "ENGLISH"),
        ("Robert", "Johnson", "ENGLISH"),
        ("Francois", "Dupont", "FRENCH"),
        ("Luc", "Moreau", "FRENCH"),
        ("Jan", "De Vries", "DUTCH"),
        ("Niels", "Van Den Berg", "DUTCH"),
        ("Lukas", "Muller", "GERMANIC"),
        ("Timo", "Schneider", "GERMANIC"),
        ("Petr", "Sokolov", "SLAVIC"),
        ("Danylo", "Kovalenko", "SLAVIC"),
    ],
)
def test_fixtures_conocidos(classifier, first, last, profile):
    result, confidence = classifier.classify(first=first, last=last)
    assert result == profile
    assert result in VALID_PROFILES
    assert confidence >= 0.6


@pytest.mark.parametrize(
    "first,last",
    [
        ("Chester", "Brocklehurst"),
        ("Leif", "Okonomiya"),
        ("Axel", "Kwiatkowski"),
        ("Bjorn", "Halvorsen"),
    ],
)
def test_fixture_desconocido_cae_unknown(classifier, first, last):
    result, confidence = classifier.classify(first=first, last=last)
    assert result == "UNKNOWN"
    assert 0.0 <= confidence < 0.62


def test_sin_umbral_de_confianza_desconocido(classifier):
    # Un único hit de given (0.7) no alcanza el umbral → UNKNOWN.
    result, confidence = classifier.classify(first="Miguel", last="Xyzzzk")
    assert result == "UNKNOWN"
    assert confidence < 0.62


def test_doble_origen_devuelve_multi_origin(classifier):
    # "Martín" es apellido en las pools inglés y francés (mismo peso → empate).
    result, _ = classifier.classify(first="Carlos", last="Martin")
    assert result == "MULTI_ORIGIN"


def test_confidence_monotona_con_hits(classifier):
    _, weak = classifier.classify(first="John", last="Smithfield")
    _, strong = classifier.classify(first="John", last="Smith")
    assert weak < strong