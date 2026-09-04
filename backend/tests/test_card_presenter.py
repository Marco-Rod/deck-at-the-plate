"""
Pruebas de caracterización de los presenters de cartas (lógica extraída de gameplay.py:
dict-builders de pitcher/bateador que estaban duplicados).
"""
from types import SimpleNamespace

from app.services.card_presenter import (
    build_batter_payload,
    build_card_base,
    build_pitcher_payload,
)


def make_card(**overrides):
    base = dict(
        id="card-1",
        name="Test Player",
        number=7,
        overall=85,
        position="SP",
        rarity=SimpleNamespace(value="COMMON"),
        team=SimpleNamespace(name="Nice Team"),
        repertoire=[
            {"pitch_type": "4-SEAM", "velocity": 95, "control": 90, "movement": 80},
            {"pitch_type": "SLIDER", "velocity": 90, "control": 85, "movement": 88},
        ],
        contact=70,
        power=75,
        velocity=95,
        control=90,
        movement=88,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_card_base():
    card = make_card()
    base = build_card_base(card)
    assert base == {
        "id": "card-1",
        "name": "Test Player",
        "number": 7,
        "overall": 85,
        "position": "SP",
        "rarity": "COMMON",
        "team": "Nice Team",
    }


def test_build_card_base_fallback_common_unknown():
    card = make_card(rarity=None, team=None)
    base = build_card_base(card)
    assert base["rarity"] == "COMMON"
    assert base["team"] == "UNKNOWN"


def test_pitcher_payload_defaults():
    payload = build_pitcher_payload(make_card())
    assert payload["role"] == "PITCHER"
    assert payload["stats"] == [
        {"label": "VEL", "val": 95},
        {"label": "CTA", "val": 90},
        {"label": "MCA", "val": 88},
    ]
    assert "repertoire" not in payload
    assert "pitch_count" not in payload
    assert "fatigue_level" not in payload
    assert "already_used" not in payload


def test_pitcher_payload_with_repertoire():
    card = make_card()
    payload = build_pitcher_payload(card, with_repertoire=True)
    assert payload["repertoire"] == card.repertoire


def test_pitcher_payload_empty_repertoire_defaults_to_list():
    payload = build_pitcher_payload(make_card(repertoire=None), with_repertoire=True)
    assert payload["repertoire"] == []


def test_pitcher_payload_with_stamina():
    payload = build_pitcher_payload(
        make_card(),
        with_stamina=True,
        pitch_count=42,
        fatigue_level=37.5,
    )
    assert payload["pitch_count"] == 42
    assert payload["fatigue_level"] == 38


def test_pitcher_payload_already_used():
    payload = build_pitcher_payload(make_card(), already_used=True)
    assert payload["already_used"] is True


def test_pitcher_payload_extra_fields():
    payload = build_pitcher_payload(make_card(), extra={"pending_change": True})
    assert payload["pending_change"] is True


def test_batter_payload():
    card = make_card(position="LF", contact=70, power=75, overall=85)
    payload = build_batter_payload(card)
    assert payload["role"] == "BATTER"
    assert payload["stats"][0]["label"] == "CON"
    assert payload["stats"][0]["val"] == 70
    assert payload["stats"][1]["val"] == 75
    # VIS = round(contact*0.7 + overall*0.3)
    assert payload["stats"][2]["val"] == int(70 * 0.70 + 85 * 0.30)


def test_batter_payload_extra_fields():
    payload = build_batter_payload(make_card(), streak=3)
    assert payload["streak"] == 3
