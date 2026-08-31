"""Pruebas unitarias de las reglas de selección del sobre inicial (starter pack).

Usa cartas fake (sin base de datos) contra la lógica pura de
``app.engine.starter_pack.select_starter_cards``.
"""

import random
from collections import Counter

import pytest

from app.engine.starter_pack import (
    TOTAL_CARDS,
    FAVORITE_TEAM_CARDS,
    OTHER_TEAMS_CARDS,
    REQUIRED_POSITIONS,
    TIER_PRIORITY,
    select_starter_cards,
)
from app.models.card import CardRarity


class FakeRarity:
    def __init__(self, name: str):
        self.name = name


class FakeCard:
    """Carta mínima necesaria para la lógica de selección.

    El ``id`` es determinista (deriva de posición/rareza/equipo) para que dos
    llamadas a los helpers de construcción produzcan cartas idénticas.
    """

    def __init__(self, position: str, rarity: str, team_id: str, is_two_way: bool = False):
        self.position = position
        self.rarity = FakeRarity(rarity)
        self.team_id = team_id
        self.is_two_way = is_two_way
        self.id = f"{team_id}_{position}_{rarity}_{is_two_way}"

    def __repr__(self):
        return f"FakeCard({self.position}, {self.rarity.name}, {self.team_id})"


PITCHER_POS = ["SP", "RP"]
FIELDER_POS = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"]


def make_team_cards():
    """Mazo completo: varias cartas por posición y por rareza, para que la
    selección tenga pool suficiente y verifique que las reglas se cumplen."""
    cards = []
    team_id = "TEAM"
    rarezas = ["COMMON", "BRONZE", "SILVER", "GOLD", "DIAMOND"]
    for pos in [*FIELDER_POS, *PITCHER_POS]:
        for rarity in rarezas:
            cards.append(FakeCard(pos, rarity, team_id))
    return cards


def make_other_team_cards():
    """Mazo de otros equipos: pitchers de cualquier rareza y fielders COMMON,
    para cubrir la garantía de lanzador y las posiciones faltantes."""
    cards = []
    for pos in PITCHER_POS:
        for rarity in ["COMMON", "BRONZE", "SILVER", "GOLD"]:
            cards.append(FakeCard(pos, rarity, "OTH"))
    for pos in FIELDER_POS:
        cards.append(FakeCard(pos, "COMMON", "OTH"))
    return cards


def _is_pitcher(card):
    return card.position in PITCHER_POS or card.is_two_way


def test_total_card_count():
    result = select_starter_cards(make_team_cards(), make_other_team_cards())
    assert len(result) == TOTAL_CARDS == 13


def test_favorite_vs_other_team_split():
    result = select_starter_cards(make_team_cards(), make_other_team_cards())
    team_cards = [c for c in result if c.team_id == "TEAM"]
    other_cards = [c for c in result if c.team_id == "OTH"]
    assert len(team_cards) == FAVORITE_TEAM_CARDS == 7
    assert len(other_cards) == OTHER_TEAMS_CARDS == 6


def test_no_duplicates():
    result = select_starter_cards(make_team_cards(), make_other_team_cards())
    ids = [c.id for c in result]
    assert len(ids) == len(set(ids))


def test_only_from_provided_pools():
    result = select_starter_cards(make_team_cards(), make_other_team_cards())
    for card in result:
        assert card.team_id in ("TEAM", "OTH")


def test_favorite_team_has_one_top_tier_card():
    result = select_starter_cards(make_team_cards(), make_other_team_cards())
    team_cards = [c for c in result if c.team_id == "TEAM"]
    top_tier = TIER_PRIORITY[0]
    top_in_team = [c for c in team_cards if c.rarity.name == top_tier]
    assert len(top_in_team) >= 1


def test_other_team_cards_are_common():
    """Las cartas de otros equipos son COMMON, salvo el/los pitcher garantizados."""
    for _ in range(50):
        result = select_starter_cards(make_team_cards(), make_other_team_cards())
        other_cards = [c for c in result if c.team_id == "OTH"]
        for card in other_cards:
            if not _is_pitcher(card):
                assert card.rarity.name == "COMMON"


def test_at_least_one_pitcher():
    for _ in range(100):
        result = select_starter_cards(make_team_cards(), make_other_team_cards())
        assert any(_is_pitcher(c) for c in result)


def test_max_two_sp_from_favorite_team():
    """El límite de 2 SP se aplica a la selección del equipo favorito."""
    for _ in range(200):
        result = select_starter_cards(make_team_cards(), make_other_team_cards())
        team_cards = [c for c in result if c.team_id == "TEAM"]
        sp_count = sum(1 for c in team_cards if c.position == "SP")
        assert sp_count <= 2


def test_missing_positions_are_filled_with_common():
    """Si falta una posición y hay cupo, se rellena con una COMMON de esa posición.

    Con el pool actual el pack debe terminar cubriendo todas las posiciones de
    campo: el equipo favorito aporta 7 y los otros llenan los huecos.
    """
    for _ in range(100):
        result = select_starter_cards(make_team_cards(), make_other_team_cards())
        required = set(REQUIRED_POSITIONS)
        covered = {c.position for c in result if c.position in required}
        assert required <= covered


@pytest.mark.parametrize("seed", list(range(50)))
def test_deterministic_with_seed(seed):
    """Con el mismo rng/seed produce la misma selección (estabilidad)."""
    rng1 = random.Random(seed)
    rng2 = random.Random(seed)
    r1 = select_starter_cards(make_team_cards(), make_other_team_cards(), rng=rng1)
    r2 = select_starter_cards(make_team_cards(), make_other_team_cards(), rng=rng2)
    assert [c.id for c in r1] == [c.id for c in r2]


def test_empty_team_returns_empty():
    assert select_starter_cards([], make_other_team_cards()) == []


def test_two_way_counts_as_pitcher():
    """Una carta two-way debe satisfacer la garantía de lanzador."""
    team_cards = [
        FakeCard("SP", "DIAMOND", "TEAM"),
        FakeCard("C", "SILVER", "TEAM"),
    ]
    other_cards = []
    for _ in range(20):
        other_cards.append(FakeCard("LF", "COMMON", "OTH"))
    # Incluir un two-way (posición no pitcher) en otros equipos
    other_cards.insert(0, FakeCard("SS", "COMMON", "OTH", is_two_way=True))
    result = select_starter_cards(team_cards, other_cards)
    assert any(_is_pitcher(c) for c in result)
