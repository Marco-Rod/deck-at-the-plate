"""
Tests de caracterización de app.engine.calculator
====================================================
Congelan el comportamiento ACTUAL de calculate_play_outcome() para que cualquier
refactor SOLID posterior pueda validarse sin cambiar de forma accidental el
resultado de los duelos.

Estos no son tests "de diseño": documentan el estado presente del RNG y sus
umbrales. Cambiar deliberadamente la mecánica del juego exigirá actualizarlos
explícitamente.
"""

import random

from app.engine.calculator import calculate_play_outcome


DEFAULT_PITCHER = {"velocidad": 50, "control": 50, "movimiento": 50}
DEFAULT_BATTER = {"contacto": 50, "poder": 50, "vision": 50}


def _uniform_sequence(values):
    """Mock de random.uniform que devuelve cada valor de la lista en orden."""
    it = iter(values)
    return lambda a, b: next(it)


# ---------------------------------------------------------------------------
# Base por bolas intencional
# ---------------------------------------------------------------------------

def test_ibb_is_always_a_ball(monkeypatch):
    monkeypatch.setattr(random, "uniform", _uniform_sequence([0.0, 0.0, 0.0]))
    event, description = calculate_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "IBB", "zone": 5},
        {"swing_type": "NORMAL", "guessed_zone": None, "guessed_pitch": None},
    )
    assert event == "BALL"
    assert "intencional" in description


# ---------------------------------------------------------------------------
# TAKE (sin swing)
# ---------------------------------------------------------------------------

def test_take_matched_zone_is_strike(monkeypatch):
    # strike_chance = 0.65 - 0.12 = 0.53 con atributos neutros y zona adivinada
    monkeypatch.setattr(random, "random", lambda: 0.2)
    event, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "TAKE", "guessed_zone": 5, "guessed_pitch": "4-SEAM"},
    )
    assert event == "STRIKE_LOOKING"


def test_take_missed_zone_is_ball(monkeypatch):
    # strike_chance 0.65; random 0.90 supera el clamp max (0.85) -> bola
    monkeypatch.setattr(random, "random", lambda: 0.90)
    event, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "TAKE", "guessed_zone": None, "guessed_pitch": None},
    )
    assert event == "BALL"


# ---------------------------------------------------------------------------
# Whiff / Foul
# ---------------------------------------------------------------------------

def test_whiff_produces_strike_swinging(monkeypatch):
    # whiff_base 32.0 con atributos neutros; uniform 0.0 siempre abanica
    monkeypatch.setattr(random, "uniform", _uniform_sequence([0.0]))
    event, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "NORMAL", "guessed_zone": None, "guessed_pitch": None},
    )
    assert event == "STRIKE_SWINGING"


def test_foul_when_contact_but_not_matching(monkeypatch):
    # 1er uniform 90 (>whiff) → contacto; 2º uniform 10 (<35) → foul
    monkeypatch.setattr(random, "uniform", _uniform_sequence([90.0, 10.0]))
    event, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "NORMAL", "guessed_zone": None, "guessed_pitch": None},
    )
    assert event == "FOUL"


def test_power_swing_increases_whiff(monkeypatch):
    # BASE 32.0 es NORMAL; con POWER sube a 40.0 → uniform 35 queda "abanicado"
    monkeypatch.setattr(random, "uniform", _uniform_sequence([35.0]))
    event, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "POWER", "guessed_zone": None, "guessed_pitch": None},
    )
    assert event == "STRIKE_SWINGING"


# ---------------------------------------------------------------------------
# Umbrales de BABIP
# ---------------------------------------------------------------------------

BABIP_CASES = [
    (50, [80.0, 80.0, 70.0], "HIT_1B"),   # 70 en 63–85
    (50, [90.0, 90.0, 88.0], "HIT_2B"),   # 88 en 85–93
    (50, [90.0, 90.0, 94.0], "HIT_3B"),   # 94 en 93–96
    (50, [80.0, 80.0, 40.0], "OUT_GROUND"),  # 40 en 25–63
    (50, [80.0, 80.0, 10.0], "OUT_FLY"),   # 10 <= 25
]


def test_babip_thresholds(monkeypatch):
    for poder, seq, expected in BABIP_CASES:
        monkeypatch.setattr(random, "uniform", _uniform_sequence(seq))
        event, _ = calculate_play_outcome(
            DEFAULT_PITCHER,
            {"contacto": 50, "poder": poder, "vision": 50},
            {"pitch_type": "4-SEAM", "zone": 5},
            {"swing_type": "NORMAL", "guessed_zone": None, "guessed_pitch": None},
        )
        assert event == expected


def test_home_run_threshold(monkeypatch):
    # power_score = (99-50)*0.4 + 80 = 99.6 > 96
    monkeypatch.setattr(random, "uniform", _uniform_sequence([90.0, 90.0, 80.0]))
    event, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        {"contacto": 50, "poder": 99, "vision": 50},
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "NORMAL", "guessed_zone": None, "guessed_pitch": None},
    )
    assert event == "HOME_RUN"


def test_matched_zone_and_pitch_gives_bonus(monkeypatch):
    # power_score = 0 + 72 + 15 (bono) = 87 → HIT_2B
    monkeypatch.setattr(random, "uniform", _uniform_sequence([80.0, 80.0, 72.0]))
    event, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "NORMAL", "guessed_zone": 5, "guessed_pitch": "4-SEAM"},
    )
    assert event == "HIT_2B"


def test_tactics_modifiers_scale_power(monkeypatch):
    # batter_pwr 2.0: (50*2-50)*0.4 = 20 + 90 = 110 -> HOME_RUN
    monkeypatch.setattr(random, "uniform", _uniform_sequence([90.0, 90.0, 90.0]))
    event, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "NORMAL", "guessed_zone": None, "guessed_pitch": None},
        tactics_modifiers={"batter_pwr": 2.0},
    )
    assert event == "HOME_RUN"