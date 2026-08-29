"""La persistencia de estadísticas debe ser atómica con la jugada."""

import asyncio
from types import SimpleNamespace

import pytest

from app.engine import game_actions


class FakePitcher:
    def get_pitch_stats(self, _pitch_type):
        return None


def test_resolve_swing_propagates_event_store_failures(monkeypatch):
    """Nunca se debe emitir una jugada que no puede registrar sus estadísticas."""
    pitcher = FakePitcher()
    batter = SimpleNamespace()
    game = SimpleNamespace(
        state_data=None,
        current_inning=1,
        is_top_inning=True,
        balls=0,
        strikes=0,
        outs=0,
        score_home=0,
        score_away=0,
    )
    state = {
        "current_pitch": {"pitch_type": "4-SEAM", "zone": 5},
        "pitch_counts": {},
        "active_pitcher": "pitcher_1",
        "active_batter": "batter_1",
        "runners": {"1b": None, "2b": None, "3b": None},
        "active_tactics": {},
        "total_innings": 9,
    }

    monkeypatch.setattr(
        game_actions,
        "get_card_by_id",
        lambda _db, card_id: pitcher if card_id == "pitcher_1" else batter,
    )
    monkeypatch.setattr(game_actions, "map_card_to_pitcher_attrs", lambda _card: {})
    monkeypatch.setattr(game_actions, "map_card_to_batter_attrs", lambda _card: {})
    monkeypatch.setattr(game_actions, "apply_pitcher_fatigue", lambda attrs, *_: attrs)
    monkeypatch.setattr(
        game_actions, "calculate_play_outcome", lambda **_kwargs: ("HIT_1B", "Hit")
    )
    monkeypatch.setattr(
        game_actions,
        "process_at_bat_transition",
        lambda *_args: (True, False, "HIT_1B", "Hit"),
    )

    def fail_record(**_kwargs):
        raise RuntimeError("event store unavailable")

    monkeypatch.setattr(game_actions, "record_game_event", fail_record)

    with pytest.raises(RuntimeError, match="event store unavailable"):
        asyncio.run(
            game_actions.resolve_swing(
                game=game,
                state=state,
                swing_type="NORMAL",
                guessed_zone=None,
                guessed_pitch=None,
                db=object(),
                game_id="game_1",
            )
        )
