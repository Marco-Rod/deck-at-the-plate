"""
Tests de caracterización de app.engine.cpu_ai
==============================================
Congelan repertorio de picheos, zonas por dificultad y decisiones de cambio.
"""

import random

from app.core.enums import Difficulty, PitchType, SwingType
from app.engine.cpu_ai import (
    _CPU_CHANGE_PROBABILITY,
    _CPU_CHANGE_WORKLOAD_THRESHOLD,
    get_cpu_pitch_action,
    get_cpu_pitcher_change_decision,
    get_cpu_swing_action,
)
from app.engine.game_rules import MIN_PITCHES_TO_CHANGE


def test_repertoire_matches_seed_values():
    values = {p.value for p in PitchType if p is not PitchType.IBB}
    assert values == {"4-SEAM", "SLIDER", "CHANGE", "CURVE", "SINKER", "CUTTER"}


def test_pitch_action_hard_uses_corners(monkeypatch):
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])
    action = get_cpu_pitch_action(Difficulty.HARD)
    assert action["zone"] in (1, 3, 7, 9)
    assert action["pitch_type"] in PitchType


def test_pitch_action_easy_uses_center(monkeypatch):
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])
    action = get_cpu_pitch_action("EASY")
    assert action["zone"] in (2, 4, 5, 6, 8)
    assert "pitch_type" in action


def test_swing_action_hard_only_normal_or_power(monkeypatch):
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])
    action = get_cpu_swing_action("HARD")
    assert action["swing_type"] in (SwingType.NORMAL, SwingType.POWER)


def test_swing_action_medium_includes_take_and_guess(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 0.99)
    monkeypatch.setattr(random, "choice", lambda seq: seq[0])
    action = get_cpu_swing_action("MEDIUM")
    assert action["swing_type"] in (SwingType.NORMAL, SwingType.POWER, SwingType.TAKE)
    assert action["guessed_zone"] is None
    assert action["guessed_pitch"] is None


def test_change_decision_requires_minimum_pitches():
    assert get_cpu_pitcher_change_decision(0, 10.0, "EASY") is False


def test_change_decision_below_threshold():
    # 1.10 < 1.20 (umbral HARD) → determinista: no cambia sin importar el RNG
    assert get_cpu_pitcher_change_decision(
        MIN_PITCHES_TO_CHANGE, 1.10, "HARD"
    ) is False


def test_change_decision_over_threshold(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 0.01)
    assert get_cpu_pitcher_change_decision(
        MIN_PITCHES_TO_CHANGE, 1.60, Difficulty.EASY
    ) is True


def test_change_decision_rollout_probability(monkeypatch):
    # Sobre el umbral EASY (1.50), la probabilidad real (0.50) decide.
    monkeypatch.setattr(random, "random", lambda: 0.99)
    assert get_cpu_pitcher_change_decision(
        MIN_PITCHES_TO_CHANGE, 1.60, Difficulty.EASY
    ) is False


def test_change_decision_default_difficulty_medium(monkeypatch):
    # Sin dificultad: umbral MEDIUM (1.35).
    monkeypatch.setattr(random, "random", lambda: 0.01)
    assert get_cpu_pitcher_change_decision(MIN_PITCHES_TO_CHANGE, 1.40) is True


def test_threshold_maps_use_difficulty_names():
    assert set(_CPU_CHANGE_WORKLOAD_THRESHOLD) == {
        Difficulty.EASY,
        Difficulty.MEDIUM,
        Difficulty.HARD,
    }
    assert set(_CPU_CHANGE_PROBABILITY) == {
        Difficulty.EASY,
        Difficulty.MEDIUM,
        Difficulty.HARD,
    }