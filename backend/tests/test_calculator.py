"""
Tests de caracterización y de política de producción de app.engine.calculator
=================================================================================
Documentan y CONGELAN la política de producción promovida en 002E-4:
    TAKE base 0.30 · floor 0.20 · ceiling 0.85 · foul/contact 0.45
Además verifican que los knobs LAB (_resolve_play_outcome) resuelven None a
producción y que pueden reproducir valores históricos (PROD 0.65/0.35/0.25,
B3-C1 0.30/0.45/0.25) sin duplicar la fórmula.

Cambiar deliberadamente el paquete de producción exigirá actualizarlos
explícitamente.
"""

import inspect
import random

from app.engine import calculator
from app.engine.calculator import _resolve_play_outcome, calculate_play_outcome


DEFAULT_PITCHER = {"velocidad": 50, "control": 50, "movimiento": 50}
DEFAULT_BATTER = {"contacto": 50, "poder": 50, "vision": 50}


def _uniform_sequence(values):
    """Mock de random.uniform que devuelve cada valor de la lista en orden."""
    it = iter(values)
    return lambda a, b: next(it)


def _no_foul():
    """Draw de foul alto → contacto limpio (sin FOUL)."""
    return 0.99


# ---------------------------------------------------------------------------
# Paquete de producción congelado (002E-4 · PROMOTE)
# ---------------------------------------------------------------------------

def test_production_package_constants_frozen():
    assert calculator.TAKE_BASE_STRIKE_CHANCE == 0.30
    assert calculator.TAKE_STRIKE_CHANCE_FLOOR == 0.20
    assert calculator.TAKE_STRIKE_CHANCE_CEILING == 0.85
    assert calculator.FOUL_ON_CONTACT_CHANCE == 0.45


def test_take_default_base_is_030():
    # Zona no adivinada, atributos neutros, floor 0.20: strike_chance = 0.30.
    assert calculator._take_strike_probability(0.30, 50, 50, False, 0.20) == 0.30


def test_take_monotonicity_control_up_strike_up():
    # CTL ↑ → strike_chance ↑ (peso 0.003); VIS fija, floor 0.20.
    low = calculator._take_strike_probability(0.30, 45, 70, False, 0.20)
    mid = calculator._take_strike_probability(0.30, 70, 70, False, 0.20)
    high = calculator._take_strike_probability(0.30, 95, 70, False, 0.20)
    assert low < mid < high


def test_take_monotonicity_vision_up_strike_down():
    # VIS ↑ → strike_chance ↓ (peso 0.002); CTL fijo, floor 0.20.
    low = calculator._take_strike_probability(0.30, 70, 45, False, 0.20)
    high = calculator._take_strike_probability(0.30, 70, 95, False, 0.20)
    assert high < low


def test_take_low_ctl_high_vis_floor_window():
    # CTL45/VIS95 raw = 0.195: baja de 0.25 pero NUNCA de 0.20 (floor 002E-4).
    prob = calculator._take_strike_probability(0.30, 45, 95, False, 0.20)
    assert prob == 0.20
    assert prob < 0.25
    # Sin floor (None → 0.0) cae al raw, para poder reproducir NO-FLOOR.
    raw = calculator._take_strike_probability(0.30, 45, 95, False, 0.0)
    assert abs(raw - 0.195) < 1e-9


def test_take_clamp_regression_clamp001():
    # CLAMP-001: con el piso 0.20 el rincón ya NO colapsa en una meseta plana.
    # CTL45/VIS95 (0.20) debe quedar MENOS disciplinado que CTL45/VIS70 (0.245).
    vis70 = calculator._take_strike_probability(0.30, 45, 70, False, 0.20)
    vis95 = calculator._take_strike_probability(0.30, 45, 95, False, 0.20)
    assert abs(vis70 - 0.245) < 1e-9
    assert vis95 == 0.20
    assert vis95 < vis70


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
    # strike_chance = 0.30 - 0.12 = 0.18 con zona adivinada; draw 0.10 → strike.
    monkeypatch.setattr(random, "random", lambda: 0.10)
    event, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "TAKE", "guessed_zone": 5, "guessed_pitch": "4-SEAM"},
    )
    assert event == "STRIKE_LOOKING"


def test_take_missed_zone_is_ball(monkeypatch):
    # strike_chance 0.30 (zona no adivinada); draw 0.90 supera al techo 0.85 → bola.
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
    # uniform 90 (>whiff) → contacto; draw random 0.40 (<0.45) → FOUL.
    monkeypatch.setattr(random, "uniform", _uniform_sequence([90.0]))
    monkeypatch.setattr(random, "random", lambda: 0.40)
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
    (50, [80.0, 70.0], "HIT_1B"),   # power 70 en 63–85
    (50, [90.0, 88.0], "HIT_2B"),   # 88 en 85–93
    (50, [90.0, 94.0], "HIT_3B"),   # 94 en 93–96
    (50, [80.0, 40.0], "OUT_GROUND"),  # 40 en 25–63
    (50, [80.0, 10.0], "OUT_FLY"),   # 10 <= 25
]


def test_babip_thresholds(monkeypatch):
    for poder, seq, expected in BABIP_CASES:
        monkeypatch.setattr(random, "uniform", _uniform_sequence(seq))
        monkeypatch.setattr(random, "random", _no_foul)
        event, _ = calculate_play_outcome(
            DEFAULT_PITCHER,
            {"contacto": 50, "poder": poder, "vision": 50},
            {"pitch_type": "4-SEAM", "zone": 5},
            {"swing_type": "NORMAL", "guessed_zone": None, "guessed_pitch": None},
        )
        assert event == expected


def test_home_run_threshold(monkeypatch):
    # power_score = (99-50)*0.4 + 80 = 99.6 > 96
    monkeypatch.setattr(random, "uniform", _uniform_sequence([90.0, 80.0]))
    monkeypatch.setattr(random, "random", _no_foul)
    event, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        {"contacto": 50, "poder": 99, "vision": 50},
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "NORMAL", "guessed_zone": None, "guessed_pitch": None},
    )
    assert event == "HOME_RUN"


def test_matched_zone_and_pitch_gives_bonus(monkeypatch):
    # power_score = 0 + 72 + 15 (bono) = 87 → HIT_2B
    monkeypatch.setattr(random, "uniform", _uniform_sequence([80.0, 72.0]))
    monkeypatch.setattr(random, "random", _no_foul)
    event, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "NORMAL", "guessed_zone": 5, "guessed_pitch": "4-SEAM"},
    )
    assert event == "HIT_2B"


def test_tactics_modifiers_scale_power(monkeypatch):
    # batter_pwr 2.0: (50*2-50)*0.4 = 20 + 90 = 110 -> HOME_RUN
    monkeypatch.setattr(random, "uniform", _uniform_sequence([90.0, 90.0]))
    monkeypatch.setattr(random, "random", _no_foul)
    event, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "NORMAL", "guessed_zone": None, "guessed_pitch": None},
        tactics_modifiers={"batter_pwr": 2.0},
    )
    assert event == "HOME_RUN"


# ---------------------------------------------------------------------------
# Frontera LAB vs PRODUCCIÓN (002C-B / 002C-C / 002E-4)
# ---------------------------------------------------------------------------

def test_public_api_has_no_lab_knobs():
    params = inspect.signature(calculate_play_outcome).parameters
    assert "take_bias" not in params
    assert "foul_chance" not in params
    assert "take_floor" not in params


def test_lab_resolver_accepts_knobs():
    params = inspect.signature(_resolve_play_outcome).parameters
    assert "take_bias" in params
    assert "foul_chance" in params
    assert "take_floor" in params


def test_public_api_equals_lab_resolver_without_knobs(monkeypatch):
    # Sin overrides, el resolver LAB y la API pública (que delega en él) producen
    # el mismo resultado con la misma secuencia de RNG: una sola fórmula.
    case = {
        "pitcher_attrs": DEFAULT_PITCHER,
        "batter_attrs": DEFAULT_BATTER,
        "pitch_selected": {"pitch_type": "4-SEAM", "zone": 5},
        "swing_selected": {"swing_type": "NORMAL", "guessed_zone": None, "guessed_pitch": None},
    }
    monkeypatch.setattr(random, "uniform", _uniform_sequence([90.0, 70.0]))
    monkeypatch.setattr(random, "random", _no_foul)
    public_event, public_desc = calculate_play_outcome(**case)
    monkeypatch.setattr(random, "uniform", _uniform_sequence([90.0, 70.0]))
    monkeypatch.setattr(random, "random", _no_foul)
    lab_event, lab_desc = _resolve_play_outcome(**case)
    assert (public_event, public_desc) == (lab_event, lab_desc)


def test_take_bias_override_changes_take(monkeypatch):
    # Zona no adivinada, draw 0.40: producción (0.30) lo canta bola; el LAB con
    # take_bias=0.65 (PROD histórico) lo canta strike.
    monkeypatch.setattr(random, "random", lambda: 0.40)
    event_prod, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "TAKE", "guessed_zone": None, "guessed_pitch": None},
    )
    monkeypatch.setattr(random, "random", lambda: 0.40)
    event_lab, _ = _resolve_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "TAKE", "guessed_zone": None, "guessed_pitch": None},
        take_bias=0.65, take_floor=0.25,
    )
    assert event_prod == "BALL"
    assert event_lab == "STRIKE_LOOKING"


def test_take_floor_override_changes_take():
    # floor 0.20 vs 0.25 (CLAMP-001): la zona LOW CTL/HIGH VIS deja el valor 0.20
    # en el 002E-4 (0.195→0.20) y sigue colapsando al 0.25 histórico (0.195→0.25).
    e4 = calculator._take_strike_probability(0.30, 45, 95, False, 0.20)
    historical = calculator._take_strike_probability(0.30, 45, 95, False, 0.25)
    assert e4 == 0.20
    assert historical == 0.25


def test_foul_chance_override_changes_contact(monkeypatch):
    # Contacto sin acertar zona ni picheo, draw random 0.40: producción (0.45)
    # canta FOUL; el LAB con foul_chance=0.35 (PROD histórico) deja contacto
    # limpio → HIT_1B.
    monkeypatch.setattr(random, "uniform", _uniform_sequence([90.0]))
    monkeypatch.setattr(random, "random", lambda: 0.40)
    event_prod, _ = calculate_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "NORMAL", "guessed_zone": None, "guessed_pitch": None},
    )
    monkeypatch.setattr(random, "uniform", _uniform_sequence([90.0, 70.0]))
    monkeypatch.setattr(random, "random", lambda: 0.40)
    event_lab, _ = _resolve_play_outcome(
        DEFAULT_PITCHER,
        DEFAULT_BATTER,
        {"pitch_type": "4-SEAM", "zone": 5},
        {"swing_type": "NORMAL", "guessed_zone": None, "guessed_pitch": None},
        foul_chance=0.35,
    )
    assert event_prod == "FOUL"
    assert event_lab == "HIT_1B"