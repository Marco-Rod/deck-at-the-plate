"""
Pruebas de caracterización de la fatiga del pitcher (lógica extraída de gameplay.py).
Congela la fórmula: extra = pc - threshold; fatigue = (1 - (1 - 0.1*extra)) * 100, cap 0-100.
"""
import pytest

from app.engine.fatigue_manager import compute_fatigue_level, get_pitch_threshold


def test_thresholds_by_innings():
    assert get_pitch_threshold(3) == 6
    assert get_pitch_threshold(6) == 15
    assert get_pitch_threshold(9) == 25


def test_interpolated_threshold_for_unlisted_innings():
    assert get_pitch_threshold(4) == 26  # int((60/9)*4)
    assert get_pitch_threshold(18) == 120


def test_no_fatigue_below_threshold():
    assert compute_fatigue_level(6, total_innings=3) == 0.0
    assert compute_fatigue_level(15, total_innings=6) == 0.0
    assert compute_fatigue_level(25, total_innings=9) == 0.0


def test_fatigue_starts_after_threshold():
    # 1 lanzamiento extra => penalización 10%
    assert compute_fatigue_level(26, total_innings=9) == pytest.approx(10.0)
    # 5 lanzamientos extra => 50%
    assert compute_fatigue_level(30, total_innings=9) == pytest.approx(50.0)


def test_fatigue_caps_at_100():
    # 10+ extra => penalización >= 100%
    assert compute_fatigue_level(35, total_innings=9) == 100.0
    assert compute_fatigue_level(60, total_innings=9) == 100.0


def test_fatigue_never_negative():
    assert compute_fatigue_level(0, total_innings=9) == 0.0


def test_fatigue_aggressive_at_3_innings():
    # 3 innings: threshold 6. 16 pitches => 10 extra => 100%
    assert compute_fatigue_level(16, total_innings=3) == 100.0
    # 9 pitches => 3 extra => 30%
    assert compute_fatigue_level(9, total_innings=3) == pytest.approx(30.0)