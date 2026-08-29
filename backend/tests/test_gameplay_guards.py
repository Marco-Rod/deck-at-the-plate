"""Guardas de seguridad del endpoint de jugabilidad."""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.routers.gameplay import change_pitcher
from app.schemas import ChangePitcherRequest


def test_change_pitcher_rejects_player_when_it_is_not_pitcher_turn(monkeypatch):
    game = SimpleNamespace(
        home_user_id="home_user",
        away_user_id="away_user",
        is_top_inning=True,
        state_data={
            "active_pitcher": "home_pitcher",
            "home_pitcher_id": "home_pitcher",
            "away_pitcher_id": "away_pitcher",
            "pitch_counts": {"home_pitcher": 5},
        },
    )
    monkeypatch.setattr("app.routers.gameplay.get_game_by_id", lambda *_: game)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            change_pitcher(
                game_id="game_1",
                payload=ChangePitcherRequest(new_pitcher_id="away_reliever"),
                db=object(),
                current_user_id="away_user",
            )
        )

    assert error.value.status_code == 403


def test_change_pitcher_rejects_corrupt_active_pitcher_side(monkeypatch):
    game = SimpleNamespace(
        home_user_id="home_user",
        away_user_id="away_user",
        is_top_inning=True,
        state_data={
            "active_pitcher": "away_pitcher",
            "home_pitcher_id": "home_pitcher",
            "away_pitcher_id": "away_pitcher",
            "pitch_counts": {"away_pitcher": 5},
        },
    )
    monkeypatch.setattr("app.routers.gameplay.get_game_by_id", lambda *_: game)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            change_pitcher(
                game_id="game_1",
                payload=ChangePitcherRequest(new_pitcher_id="home_reliever"),
                db=object(),
                current_user_id="home_user",
            )
        )

    assert error.value.status_code == 409
