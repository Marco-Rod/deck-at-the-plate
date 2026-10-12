"""Política de conversión de arsenal Statcast al vocabulario del runtime."""

from dataclasses import dataclass

from app.core.enums import PitchFamily
from etl.services.pitch_repertoire import build_runtime_repertoire
from etl.validators.catalog_gameplay import validate_pitcher_repertoires


@dataclass
class PitchProfile:
    pitch_type: str
    pitch_count: int
    usage_rate: float
    pitch_family: PitchFamily


@dataclass
class Card:
    id: str
    position: str
    repertoire: list[dict]
    is_two_way: bool = False


def test_runtime_repertoire_maps_deduplicates_and_limits_to_four():
    profiles = [
        PitchProfile("FF", 50, 0.50, PitchFamily.FASTBALL),
        PitchProfile("FA", 40, 0.40, PitchFamily.FASTBALL),
        PitchProfile("SL", 30, 0.30, PitchFamily.BREAKING),
        PitchProfile("CH", 20, 0.20, PitchFamily.OFFSPEED),
        PitchProfile("CU", 10, 0.10, PitchFamily.BREAKING),
        PitchProfile("KN", 5, 0.05, PitchFamily.OTHER),
    ]

    repertoire = build_runtime_repertoire(profiles)

    assert [pitch["pitch_type"] for pitch in repertoire] == [
        "4-SEAM", "SLIDER", "CHANGE", "CURVE"
    ]
    assert repertoire[0]["source_pitch_type"] == "FF"
    assert all(pitch["pitch_type"] != "KN" for pitch in repertoire)


def test_repertoire_gate_rejects_pitcher_without_supported_pitch():
    cards = [
        Card(id="valid", position="SP", repertoire=[{"pitch_type": "4-SEAM"}]),
        Card(id="invalid", position="RP", repertoire=[{"pitch_type": "FF"}]),
    ]

    result = validate_pitcher_repertoires(cards)

    assert not result.ok
    assert "invalid: repertorio inválido" in result.detail
