"""Contrato de reconciliación P5-C (Paso 7) sobre la API real.

Verifica que, tras jugar una partida real, las tres representaciones concuerdan
(event stream ↔ estado persistido ↔ box score ↔ pitch log) y que el verificador
DETECTA una divergencia inyectada (no es un no-op).
"""

from __future__ import annotations

from app.models import GameEventLog, GameSession
from app.services.game_reconciliation import reconcile_game_from_db


def _bottom_state(ctx):
    """State_data de la media Baja (el humano HOME batea)."""
    lineup = ctx["roster"]["lineup"]
    return {
        "current_pitch": None,
        "active_batter": lineup[0],
        "home_batter_index": 0,
        "runners": {"1b": None, "2b": None, "3b": None},
        "active_tactics": {"home": None, "away": None},
    }


def _swing(client, game_id, headers):
    return client.post(
        f"/api/v1/games/{game_id}/swing",
        json={"swing_type": "NORMAL", "guessed_zone": 5},
        headers=headers,
    )


def _play_a_few_plate_appearances(client, ctx, seed_session, target=2):
    gid = ctx["game_id"]
    for _ in range(80):
        resp = _swing(client, gid, ctx["headers"])
        assert resp.status_code == 200, resp.text
        seed_session.expire_all()
        count = (
            seed_session.query(GameEventLog)
            .filter(GameEventLog.game_id == gid)
            .count()
        )
        if count >= target:
            return
    raise AssertionError("no se cerró ningún plate appearance en 80 swings")


def _load_game(seed_session, game_id):
    seed_session.expire_all()
    return seed_session.query(GameSession).filter(GameSession.id == game_id).one()


def test_partida_jugada_reconcilia(client, game_factory, mutate_game, seed_session):
    ctx = game_factory()
    gid = ctx["game_id"]
    mutate_game(gid, columns={"is_top_inning": False}, state=_bottom_state(ctx))

    _play_a_few_plate_appearances(client, ctx, seed_session)

    game = _load_game(seed_session, gid)
    issues = reconcile_game_from_db(seed_session, game)
    assert issues == [], [str(i) for i in issues]

    # El stream nunca registra el envoltorio GAME_OVER como evento de jugada.
    events = (
        seed_session.query(GameEventLog)
        .filter(GameEventLog.game_id == gid)
        .all()
    )
    assert all(e.event_type != "GAME_OVER" for e in events)


def test_el_verificador_detecta_una_divergencia_inyectada(
    client, game_factory, mutate_game, seed_session
):
    ctx = game_factory()
    gid = ctx["game_id"]
    mutate_game(gid, columns={"is_top_inning": False}, state=_bottom_state(ctx))

    _play_a_few_plate_appearances(client, ctx, seed_session)

    # Un juego sano reconcilia…
    game = _load_game(seed_session, gid)
    assert reconcile_game_from_db(seed_session, game) == []

    # …y una divergencia inyectada (marcador vs stream) se reporta.
    game.score_home += 7
    seed_session.commit()

    game = _load_game(seed_session, gid)
    codes = {i.code for i in reconcile_game_from_db(seed_session, game)}
    assert "runs.home_state_vs_stream" in codes
