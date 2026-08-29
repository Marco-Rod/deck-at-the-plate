"""
Tests de caracterización de app.engine.runner_manager
========================================================
Congelan el comportamiento actual de advance_runners() (avance de corredores
y anotación) implementado con cadenas if/elif por evento.
"""

import random

from app.engine.runner_manager import advance_runners


EMPTY = {"1b": None, "2b": None, "3b": None}


def _loaded():
    return {"1b": "P1", "2b": "P2", "3b": "P3"}


# ---------------------------------------------------------------------------
# WALK
# ---------------------------------------------------------------------------

def test_walk_empty_bases_puts_batter_on_first():
    runners, runs, event = advance_runners(EMPTY, "WALK", "BATTER")
    assert runners == {"1b": "BATTER", "2b": None, "3b": None}
    assert runs == 0
    assert event == "WALK"


def test_walk_with_bases_loaded_forces_one_run():
    runners, runs, event = advance_runners(_loaded(), "WALK", "BATTER")
    assert runners == {"1b": "BATTER", "2b": "P1", "3b": "P2"}
    assert runs == 1  # P3 anota por avance forzado


# ---------------------------------------------------------------------------
# HITS
# ---------------------------------------------------------------------------

def test_single_advances_and_scores_from_third():
    runners, runs, event = advance_runners(_loaded(), "HIT_1B", "BATTER")
    assert runners == {"1b": "BATTER", "2b": "P1", "3b": "P2"}
    assert runs == 1  # solo P3 anota
    assert event == "HIT_1B"


def test_double_scores_two_and_puts_batter_on_second():
    runners, runs, event = advance_runners(_loaded(), "HIT_2B", "BATTER")
    assert runners == {"1b": None, "2b": "BATTER", "3b": "P1"}
    assert runs == 2


def test_triple_scores_three_and_puts_batter_on_third():
    runners, runs, event = advance_runners(_loaded(), "HIT_3B", "BATTER")
    assert runners == {"1b": None, "2b": None, "3b": "BATTER"}
    assert runs == 3


def test_home_run_clears_base_with_loaded_bases():
    runners, runs, event = advance_runners(_loaded(), "HOME_RUN", "BATTER")
    assert runners == EMPTY
    assert runs == 4


def test_home_run_with_no_runners_scores_one():
    runners, runs, event = advance_runners(EMPTY, "HOME_RUN", "BATTER")
    assert runners == EMPTY
    assert runs == 1


# ---------------------------------------------------------------------------
# Outs en juego
# ---------------------------------------------------------------------------

def test_ground_out_with_runner_on_first_is_double_play(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 0.1)  # 0.1 < 0.75 → DP
    runners, runs, event = advance_runners({"1b": "P1", "2b": None, "3b": None}, "OUT_GROUND", "BATTER")
    assert event == "DOUBLE_PLAY"
    assert runners == EMPTY  # P1 out en 2B, bateador out en 1B
    assert runs == 0


def test_double_play_with_loaded_bases_runs_third(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 0.1)
    runners, runs, event = advance_runners(_loaded(), "OUT_GROUND", "BATTER")
    assert event == "DOUBLE_PLAY"
    assert runners == {"1b": None, "2b": None, "3b": "P2"}  # P2 avanza a 3B
    assert runs == 1  # P3 anota por fuerza


def test_ground_out_without_double_play_keeps_runners(monkeypatch):
    # Solo corredor en 1B (dp_chance 0.75); 0.9 > 0.75 → sin DP
    monkeypatch.setattr(random, "random", lambda: 0.9)
    runners, runs, event = advance_runners({"1b": "P1", "2b": None, "3b": None}, "OUT_GROUND", "BATTER")
    assert event == "OUT_GROUND"
    assert runners == {"1b": "P1", "2b": None, "3b": None}
    assert runs == 0


def test_fly_out_keeps_runners_in_place():
    runners, runs, event = advance_runners(_loaded(), "OUT_FLY", "BATTER")
    assert runners == _loaded()
    assert runs == 0
    assert event == "OUT_FLY"


def test_unknown_event_keeps_runners_in_place():
    runners, runs, event = advance_runners(_loaded(), "STRIKEOUT", "BATTER")
    assert runners == _loaded()
    assert runs == 0
    assert event == "STRIKEOUT"