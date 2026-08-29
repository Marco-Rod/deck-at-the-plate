"""
Pruebas de caracterización de las utilidades CPU movidas desde gameplay.py:
is_cpu_turn y choose_pitch_from_repertoire.
"""
from types import SimpleNamespace

from app.engine.cpu_ai import choose_pitch_from_repertoire, is_cpu_turn


def make_game(home="player1", away="player2", is_top_inning=True):
    return SimpleNamespace(
        home_user_id=home,
        away_user_id=away,
        is_top_inning=is_top_inning,
    )


def make_state(mode="PVE", is_game_over=False):
    return {"mode": mode, "is_game_over": is_game_over}


# ── is_cpu_turn ──────────────────────────────────────────────────────

def test_cpu_home_pitches_on_top_inning():
    assert is_cpu_turn(make_game(home="CPU_BOT", is_top_inning=True), make_state(), "PITCHER") is True
    assert is_cpu_turn(make_game(home="CPU_BOT", is_top_inning=True), make_state(), "BATTER") is False


def test_cpu_home_bats_on_bottom_inning():
    assert is_cpu_turn(make_game(home="CPU_BOT", is_top_inning=False), make_state(), "PITCHER") is False
    assert is_cpu_turn(make_game(home="CPU_BOT", is_top_inning=False), make_state(), "BATTER") is True


def test_cpu_away_bats_on_top_inning():
    assert is_cpu_turn(make_game(away="CPU_BOT", is_top_inning=True), make_state(), "PITCHER") is False
    assert is_cpu_turn(make_game(away="CPU_BOT", is_top_inning=True), make_state(), "BATTER") is True


def test_cpu_away_pitches_on_bottom_inning():
    assert is_cpu_turn(make_game(away="CPU_BOT", is_top_inning=False), make_state(), "PITCHER") is True
    assert is_cpu_turn(make_game(away="CPU_BOT", is_top_inning=False), make_state(), "BATTER") is False


def test_not_pve_returns_false():
    assert is_cpu_turn(make_game(), make_state(mode="PVP"), "PITCHER") is False
    assert is_cpu_turn(make_game(), make_state(mode="PVP"), "BATTER") is False


def test_game_over_returns_false():
    assert is_cpu_turn(make_game(), make_state(is_game_over=True), "PITCHER") is False


def test_no_cpu_in_game_returns_false():
    assert is_cpu_turn(make_game(home="p1", away="p2"), make_state(), "PITCHER") is False
    assert is_cpu_turn(make_game(home="p1", away="p2"), make_state(), "BATTER") is False


def test_unknown_role_returns_false():
    assert is_cpu_turn(make_game(), make_state(), "COACH") is False


# ── choose_pitch_from_repertoire ─────────────────────────────────────

def test_returns_pitch_type_from_repertoire():
    repertoire = [{"pitch_type": "4-SEAM"}, {"pitch_type": "SLIDER"}]
    pitch = choose_pitch_from_repertoire(repertoire)
    assert pitch in ("4-SEAM", "SLIDER")


def test_empty_repertoire_returns_none():
    assert choose_pitch_from_repertoire(None) is None
    assert choose_pitch_from_repertoire([]) is None