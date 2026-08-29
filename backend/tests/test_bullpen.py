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

    state = make_state()
    old_pitcher_id, error = bullpen.apply_human_pitcher_change(
        db=object(),
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


def test_list_user_pitchers_delegates_inventory_and_marks_used(monkeypatch):
    cards = [SimpleNamespace(id="pitcher_usado"), SimpleNamespace(id="pitcher_nuevo")]
    calls = []
    monkeypatch.setattr(
        bullpen,
        "find_user_inventory_pitchers",
        lambda _db, user_id, excluded_id: calls.append((user_id, excluded_id)) or cards,
    )
    monkeypatch.setattr(
        bullpen,
        "build_pitcher_payload",
        lambda card, already_used: {"id": card.id, "already_used": already_used},
    )

    result = bullpen.list_user_available_pitchers(
        object(),
        {"active_pitcher": "pitcher_actual", "pitch_counts": {"pitcher_usado": 4}},
        "user_1",
    )

    assert calls == [("user_1", "pitcher_actual")]
    assert result == [
        {"id": "pitcher_usado", "already_used": True},
        {"id": "pitcher_nuevo", "already_used": False},
    ]


def test_list_rival_pitchers_uses_requesting_player_side(monkeypatch):
    reference_pitcher = SimpleNamespace(team_id="RIV")
    reliever = SimpleNamespace(id="reliever_1")
    monkeypatch.setattr(bullpen, "get_card_by_id", lambda *_: reference_pitcher)
    monkeypatch.setattr(
        bullpen,
        "find_pitchers_for_team",
        lambda _db, team_id, excluded_id: [reliever],
    )
    monkeypatch.setattr(
        bullpen,
        "build_pitcher_payload",
        lambda card, already_used: {"id": card.id, "already_used": already_used},
    )

    result, error = bullpen.list_rival_available_pitchers(
        object(),
        {
            "home_pitcher_id": "home_pitcher",
            "away_pitcher_id": "away_pitcher",
            "active_pitcher": "home_pitcher",
            "pitch_counts": {},
        },
        user_is_home=True,
    )

    assert error == ""
    assert result == [{"id": "reliever_1", "already_used": False}]


def test_acknowledge_pending_pitcher_change_clears_only_pending_state():
    state = {
        "awaiting_pitcher_change_acknowledgment": True,
        "pending_pitcher_change": {"old_pitcher_id": "old", "new_pitcher_id": "new"},
        "active_pitcher": "new",
    }

    assert bullpen.acknowledge_pending_pitcher_change(state) is True
    assert state == {
        "awaiting_pitcher_change_acknowledgment": False,
        "pending_pitcher_change": None,
        "active_pitcher": "new",
    }
