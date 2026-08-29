"""
Tests de caracterización de app.engine.tactical_actions
==========================================================
Congelan el comportamiento actual de resolve_bunt() y resolve_steal().
"""

import random

from app.engine.tactical_actions import resolve_bunt, resolve_steal


PITCHER = {"velocidad": 50, "control": 50, "movimiento": 50}
BATTER = {"contacto": 50, "poder": 50, "vision": 50}


# ---------------------------------------------------------------------------
# resolve_bunt
# ---------------------------------------------------------------------------

def test_bunt_success_returns_ground_out(monkeypatch):
    # chance 0.75 con atributos neutros; 0.1 < 0.75 → éxito
    monkeypatch.setattr(random, "random", lambda: 0.1)
    event, description, success = resolve_bunt(PITCHER, BATTER, {})
    assert success is True
    assert event == "OUT_GROUND"
    assert "sacrificio" in description


def test_bunt_failure_returns_strike_looking(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 0.9)
    event, _, success = resolve_bunt(PITCHER, BATTER, {})
    assert success is False
    assert event == "STRIKE_LOOKING"


def test_bunt_success_is_capped_at_90_percent(monkeypatch):
    # raw = 0.75 + (99-50)*0.003 - (0-50)*0.002 ≈ 0.997 → clamp a 0.90
    # 0.92 > 0.90 → falla (sin clamp habría sido éxito: 0.92 < 0.997)
    monkeypatch.setattr(random, "random", lambda: 0.92)
    _, _, success = resolve_bunt(
        {"control": 0, "velocidad": 50},
        {"contacto": 99, "poder": 50, "vision": 50},
        {},
    )
    assert success is False


# ---------------------------------------------------------------------------
# resolve_steal
# ---------------------------------------------------------------------------

def test_steal_invalid_target():
    success, _ = resolve_steal(PITCHER, {"1b": "P1", "2b": None, "3b": None}, "1b")
    assert success is False


def test_steal_without_runner_on_base():
    success, _ = resolve_steal(PITCHER, {"1b": None, "2b": None, "3b": None}, "2b")
    assert success is False


def test_steal_success(monkeypatch):
    # chance = 0.68 - (50*0.002 + 50*0.002) = 0.48; 0.1 < 0.48 → éxito
    monkeypatch.setattr(random, "random", lambda: 0.1)
    success, description = resolve_steal(PITCHER, {"1b": "P1", "2b": None, "3b": None}, "2b")
    assert success is True
    assert "2B" in description


def test_steal_failure(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 0.9)
    success, description = resolve_steal(PITCHER, {"1b": "P1", "2b": None, "3b": None}, "2b")
    assert success is False
    assert "Out" in description