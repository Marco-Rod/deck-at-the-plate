"""Gates puros de jugabilidad para catálogos candidatos."""

from dataclasses import dataclass

from app.models.card import CardRarity
from etl.validators.catalog_gameplay import (
    validate_cpu_roster_coverage,
    validate_starter_pack_coverage,
)


@dataclass
class Card:
    id: str
    team_id: str
    position: str
    rarity: CardRarity
    is_two_way: bool = False


def _card(team_id: str, position: str, index: int, rarity: CardRarity = CardRarity.COMMON) -> Card:
    return Card(id=f"{team_id}-{position}-{index}", team_id=team_id, position=position, rarity=rarity)


def _playable_cards() -> list[Card]:
    positions = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH", "SP", "RP"]
    cards: list[Card] = []
    for team_id in ("A", "B"):
        for index, position in enumerate(positions):
            rarity = CardRarity.DIAMOND if index == 0 else CardRarity.COMMON
            cards.append(_card(team_id, position, index, rarity))
    return cards


def test_cpu_roster_requires_nine_batters_and_two_pitchers():
    cards = _playable_cards()
    assert validate_cpu_roster_coverage(cards, ["A", "B"]).ok

    incomplete = [card for card in cards if not (card.team_id == "B" and card.position == "RP")]
    result = validate_cpu_roster_coverage(incomplete, ["A", "B"])

    assert not result.ok
    assert any("B: bateadores=9/9, pitchers=1/2" in line for line in result.detail)


def test_starter_pack_gate_uses_real_selector_and_reports_missing_defensive_position():
    cards = _playable_cards()
    assert validate_starter_pack_coverage(cards, ["A", "B"]).ok

    without_primary_dh = [card for card in cards if card.position != "DH"]
    assert validate_starter_pack_coverage(without_primary_dh, ["A", "B"]).ok

    incomplete = [card for card in cards if card.position != "RF"]
    result = validate_starter_pack_coverage(incomplete, ["A", "B"])

    assert not result.ok
    assert any(line.startswith("B: starter=") for line in result.detail)
