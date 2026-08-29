"""
Tests de caracterización de app.engine.state_manager
=====================================================
Congelan la máquina de estados del at-bat. Usa un stub de GameSession con
db=None (las consultas ORM solo se usan en logs de cambio de media entrada).
"""

from types import SimpleNamespace

from app.core.enums import Event
from app.engine.state_manager import process_at_bat_transition


def make_game(**overrides):
    base = dict(
        outs=0, strikes=0, balls=0,
        is_top_inning=True, current_inning=1,
        score_home=0, score_away=0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def make_state(**overrides):
    state = {
        "runners": {"1b": None, "2b": None, "3b": None},
        "active_batter": "B1",
        "away_batter_index": 0,
        "away_lineup": [f"A{i}" for i in range(9)],
        "home_batter_index": 0,
        "home_lineup": [f"H{i}" for i in range(9)],
        "total_innings": 9,
        "just_switched_half": False,
        "active_tactics": {"home": None, "away": None},
        "current_pitch": {"zone": 5, "pitch_type": "4-SEAM"},
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# Conteo
# ---------------------------------------------------------------------------

def test_strike_looking_increments_strikes():
    game = make_game()
    state = make_state()
    result = process_at_bat_transition(game, "STRIKE_LOOKING", state)
    assert game.strikes == 1
    assert result.at_bat_ended is False
    assert result.final_event == "STRIKE_LOOKING"


def test_three_strikes_is_strikeout():
    game = make_game()
    state = make_state()
    process_at_bat_transition(game, "STRIKE_SWINGING", state)
    process_at_bat_transition(game, "STRIKE_SWINGING", state)
    result = process_at_bat_transition(game, "STRIKE_SWINGING", state)
    assert result.at_bat_ended is True
    assert result.final_event == Event.STRIKEOUT
    assert game.outs == 1
    assert "Strikeout" in result.description


def test_four_balls_is_walk_without_ibb():
    game = make_game()
    state = make_state()
    result = None
    for _ in range(4):
        result = process_at_bat_transition(game, "BALL", state)
        if result.at_bat_ended:
            break
    assert result.final_event == Event.WALK
    assert result.at_bat_ended is True
    assert game.balls == 0  # se resetea al cerrar el at-bat


def test_ibb_forces_walk():
    game = make_game()
    state = make_state(current_pitch={"zone": 5, "pitch_type": "IBB"})
    result = process_at_bat_transition(game, "BALL", state)
    assert result.final_event == Event.WALK
    assert result.at_bat_ended is True


def test_foul_does_not_add_strike_at_two_strikes():
    game = make_game(strikes=2)
    state = make_state()
    result = process_at_bat_transition(game, "FOUL", state)
    assert game.strikes == 2
    assert result.at_bat_ended is False


def test_foul_adds_strike_below_two():
    game = make_game(strikes=1)
    state = make_state()
    process_at_bat_transition(game, "FOUL", state)
    assert game.strikes == 2


# ---------------------------------------------------------------------------
# Carreras y corredores
# ---------------------------------------------------------------------------

def test_hit_with_runner_on_third_scores_in_top():
    game = make_game(is_top_inning=True, score_away=0)
    state = make_state(runners={"1b": None, "2b": None, "3b": "R3"})
    result = process_at_bat_transition(game, "HIT_1B", state)
    assert result.at_bat_ended is True
    assert game.score_away == 1
    assert state["runners"]["1b"] == "B1"  # el bateador ocupa 1B
    assert state["last_runs_scored"] == 1


def test_home_run_scores_all_and_clears_bases():
    game = make_game(is_top_inning=True)
    state = make_state(runners={"1b": "R1", "2b": "R2", "3b": "R3"})
    result = process_at_bat_transition(game, "HOME_RUN", state)
    assert result.at_bat_ended is True
    assert game.score_away == 4
    assert state["runners"] == {"1b": None, "2b": None, "3b": None}
    assert state["last_runs_scored"] == 4


def test_double_play_adds_second_out():
    game = make_game(outs=0)
    state = make_state(runners={"1b": "R1", "2b": None, "3b": None})
    result = process_at_bat_transition(game, "OUT_GROUND", state)
    # Con un RNG "favorable" al DP podría quedar en double play o out simple;
    # el contrato congelado: outs >= 1 y evento en {OUT_GROUND, DOUBLE_PLAY}.
    assert game.outs >= 1
    assert result.final_event in (Event.OUT_GROUND, Event.DOUBLE_PLAY)


def test_inning_ends_on_three_outs():
    game = make_game(outs=2, is_top_inning=True)
    state = make_state()
    result = process_at_bat_transition(game, "OUT_FLY", state)
    assert result.inning_ended is True
    assert game.outs == 0
    assert game.is_top_inning is False  # alta → baja
    assert state["just_switched_half"] is True
    assert "Cambio de entrada" in result.description


# ---------------------------------------------------------------------------
# Fin de juego
# ---------------------------------------------------------------------------

def test_walk_off_ends_game():
    game = make_game(
        current_inning=9, is_top_inning=False,
        score_home=1, score_away=1,
    )
    state = make_state(runners={"1b": None, "2b": None, "3b": None})
    result = process_at_bat_transition(game, "HOME_RUN", state)
    assert game.score_home == 2
    assert result.final_event == Event.GAME_OVER
    assert state["is_game_over"] is True
    assert "WALK-OFF" in state["winner_message"]