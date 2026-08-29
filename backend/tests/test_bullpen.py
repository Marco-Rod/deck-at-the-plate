"""Reglas de disponibilidad y sustitución de lanzadores."""

from types import SimpleNamespace

from app.engine import bullpen


def make_state(**overrides):
    state = {
        "active_pitcher": "pitcher_actual",
        "home_pitcher_id": "pitcher_actual",
        "away_pitcher_id": "pitcher_rival",
        "pitch_counts": {"pitcher_actual": 5},
    }
    state.update(overrides)
    return state


def test_human_change_rejects_pitcher_outside_inventory(monkeypatch):
    monkeypatch.setattr(bullpen, "find_inventory_entry", lambda *args: None)

    game = SimpleNamespace()
    state = make_state()
    old_pitcher_id, error = bullpen.apply_human_pitcher_change(
        db=object(),
        game=game,
        state=state,
        new_pitcher_id="pitcher_ajeno",
        is_home_user=True,
        user_id="user_1",
    )

    assert old_pitcher_id is None
    assert error == "No puedes usar un lanzador que no está en tu inventario."
    assert state["active_pitcher"] == "pitcher_actual"


def test_human_change_rejects_pitcher_that_already_played(monkeypatch):
    monkeypatch.setattr(bullpen, "find_inventory_entry", lambda *args: object())
    monkeypatch.setattr(
        bullpen, "get_card_by_id", lambda *args: SimpleNamespace(is_pitcher=True)
    )

    state = make_state(pitch_counts={"pitcher_actual": 5, "pitcher_usado": 0})
    old_pitcher_id, error = bullpen.apply_human_pitcher_change(
        db=object(),
        game=SimpleNamespace(),
        state=state,
        new_pitcher_id="pitcher_usado",
        is_home_user=True,
        user_id="user_1",
    )

    assert old_pitcher_id is None
    assert error == "Ese lanzador ya participó en esta partida y no puede reingresar."
    assert state["active_pitcher"] == "pitcher_actual"


def test_human_change_uses_owned_unused_pitcher(monkeypatch):
    monkeypatch.setattr(bullpen, "find_inventory_entry", lambda *args: object())
    monkeypatch.setattr(
        bullpen, "get_card_by_id", lambda *args: SimpleNamespace(is_pitcher=True)
    )

    state = make_state()
    old_pitcher_id, error = bullpen.apply_human_pitcher_change(
        db=object(),
        game=SimpleNamespace(),
        state=state,
        new_pitcher_id="pitcher_nuevo",
        is_home_user=True,
        user_id="user_1",
    )

    assert error is None
    assert old_pitcher_id == "pitcher_actual"
    assert state["active_pitcher"] == "pitcher_nuevo"
    assert state["home_pitcher_id"] == "pitcher_nuevo"
    assert state["pitch_counts"]["pitcher_nuevo"] == 0
