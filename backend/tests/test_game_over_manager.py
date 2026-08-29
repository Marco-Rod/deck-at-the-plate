"""
Tests de caracterización de app.engine.game_over_manager
=========================================================
Congelan las tres reglas de fin de juego de check_game_over().
"""

from types import SimpleNamespace

from app.engine.game_over_manager import check_game_over


def make_game(**overrides):
    base = dict(
        outs=0,
        current_inning=9,
        is_top_inning=True,
        score_home=0,
        score_away=0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def make_state(**overrides):
    state = {
        "total_innings": 9,
        "just_switched_half": False,
    }
    state.update(overrides)
    return state


def test_walk_off_bottom_of_last_inning():
    game = make_game(is_top_inning=False, score_home=3, score_away=2)
    state = make_state()
    is_over, message = check_game_over(game, state)
    assert is_over is True
    assert "WALK-OFF" in message


def test_tie_at_end_of_top_is_not_decided():
    # Empate en la baja recién iniciada: ni walk-off ni victoria local directa
    game = make_game(is_top_inning=False, score_home=2, score_away=2, outs=0)
    state = make_state(just_switched_half=True)
    is_over, _ = check_game_over(game, state)
    assert is_over is False


def test_home_wins_at_end_of_top():
    game = make_game(is_top_inning=False, score_home=3, score_away=2, outs=0)
    state = make_state(just_switched_half=True)
    is_over, message = check_game_over(game, state)
    assert is_over is True
    assert "local gana" in message


def test_away_wins_after_final_inning():
    game = make_game(is_top_inning=True, current_inning=10, score_away=4, score_home=2)
    state = make_state(just_switched_half=True)
    is_over, message = check_game_over(game, state)
    assert is_over is True
    assert "visitante gana" in message


def test_no_decision_mid_game():
    game = make_game(current_inning=3, score_home=1, score_away=0)
    state = make_state()
    is_over, message = check_game_over(game, state)
    assert is_over is False
    assert message == ""