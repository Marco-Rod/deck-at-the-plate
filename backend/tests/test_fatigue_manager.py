"""
Pruebas de la fatiga del pitcher (Fatigue Policy v2).

Threshold: ``round(100 * innings / 9)`` → {3: 33, 6: 67, 9: 100}.
``compute_fatigue_level`` conserva la fórmula legacy: extra = pc - threshold;
fatigue = (1 - (1 - 0.1*extra)) * 100, cap 0-100. Comparte onset con el engine
pero no su magnitud SMOOTH (deuda GAMEPLAY-FATIGUE-CPU-001).
"""
import pytest

from app.engine.fatigue_manager import compute_fatigue_level, get_pitch_threshold


def test_thresholds_by_innings():
    assert get_pitch_threshold(3) == 33
    assert get_pitch_threshold(6) == 67
    assert get_pitch_threshold(9) == 100


def test_scaled_threshold_for_other_innings():
    assert get_pitch_threshold(4) == 44  # round(100 * 4 / 9)
    assert get_pitch_threshold(18) == 200


def test_no_fatigue_below_threshold():
    assert compute_fatigue_level(33, total_innings=3) == 0.0
    assert compute_fatigue_level(67, total_innings=6) == 0.0
    assert compute_fatigue_level(100, total_innings=9) == 0.0


def test_fatigue_starts_after_threshold():
    # 1 lanzamiento extra => penalización 10%
    assert compute_fatigue_level(101, total_innings=9) == pytest.approx(10.0)
    # 5 lanzamientos extra => 50%
    assert compute_fatigue_level(105, total_innings=9) == pytest.approx(50.0)


def test_fatigue_caps_at_100():
    # 10+ extra => penalización >= 100%
    assert compute_fatigue_level(110, total_innings=9) == 100.0
    assert compute_fatigue_level(10_000, total_innings=9) == 100.0


def test_fatigue_never_negative():
    assert compute_fatigue_level(0, total_innings=9) == 0.0


def test_fatigue_aggressive_at_3_innings():
    # 3 innings: threshold 33. 43 pitches => 10 extra => 100%
    assert compute_fatigue_level(43, total_innings=3) == 100.0
    # 36 pitches => 3 extra => 30%
    assert compute_fatigue_level(36, total_innings=3) == pytest.approx(30.0)
