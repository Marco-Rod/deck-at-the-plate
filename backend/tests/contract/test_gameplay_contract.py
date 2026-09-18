"""Contract tests del router de gameplay (pitch/swing/steal/bullpen/tactics)."""

from __future__ import annotations

import uuid

import pytest

from app.engine.game_rules import MIN_PITCHES_TO_CHANGE


def _pitch(client, game_id, headers, **kwargs):
    payload = {"pitch_type": "FF", "zone": 5}
    payload.update(kwargs)
    return client.post(f"/api/v1/games/{game_id}/pitch", json=payload, headers=headers)


def _swing(client, game_id, headers, **kwargs):
    payload = {"swing_type": "NORMAL", "guessed_zone": 5}
    payload.update(kwargs)
    return client.post(f"/api/v1/games/{game_id}/swing", json=payload, headers=headers)


def _change_pitcher(client, game_id, headers, new_pitcher_id):
    return client.post(
        f"/api/v1/games/{game_id}/change-pitcher",
        json={"new_pitcher_id": new_pitcher_id},
        headers=headers,
    )


def _bottom_state(ctx):
    """State_data correspondiente a la media Baja (el humano HOME batea)."""
    lineup = ctx["roster"]["lineup"]
    return {
        "current_pitch": None,
        "active_batter": lineup[0],
        "home_batter_index": 0,
        "runners": {"1b": None, "2b": None, "3b": None},
        "active_tactics": {"home": None, "away": None},
    }


# ---------------------------------------------------------------- pitch ---


def test_pitch_feliz_top_y_cpu_responde(client, game_factory, broadcasts):
    ctx = game_factory()
    resp = _pitch(client, ctx["game_id"], ctx["headers"])
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    captured = broadcasts[ctx["game_id"]]
    types = [m["message"]["type"] for m in captured]
    assert "PITCH_COMMITTED" in types
    assert "PLAY_RESOLVED" in types
    committed = next(m for m in captured if m["message"]["type"] == "PITCH_COMMITTED")
    assert committed["channel"] == "to_game"
    assert committed["message"]["has_pitched"] is True


def test_pitch_fuera_de_turno_403(client, game_factory, mutate_game):
    ctx = game_factory()
    mutate_game(ctx["game_id"], columns={"is_top_inning": False}, state=_bottom_state(ctx))
    resp = _pitch(client, ctx["game_id"], ctx["headers"])
    assert resp.status_code == 403


def test_pitch_repertorio_invalido_400(client, game_factory):
    ctx = game_factory()
    resp = _pitch(client, ctx["game_id"], ctx["headers"], pitch_type="ZX")
    assert resp.status_code == 400
    assert "repertorio" in resp.json()["detail"]


@pytest.mark.parametrize("zone", [0, 10, 100])
def test_pitch_zona_fuera_de_rango_422(client, game_factory, zone):
    ctx = game_factory()
    resp = _pitch(client, ctx["game_id"], ctx["headers"], zone=zone)
    assert resp.status_code == 422


def test_pitch_partida_inexistente_404(client, game_factory):
    headers = game_factory()["headers"]
    resp = _pitch(client, "no-existe-partida", headers)
    assert resp.status_code == 404


def test_pitch_bloqueado_por_cambio_pendiente_403(client, game_factory, mutate_game):
    ctx = game_factory()
    mutate_game(ctx["game_id"], state={"awaiting_pitcher_change_acknowledgment": True})
    resp = _pitch(client, ctx["game_id"], ctx["headers"])
    assert resp.status_code == 403
    assert "cambió de pitcher" in resp.json()["detail"]


def test_ibb_no_requiere_repertorio(client, game_factory):
    ctx = game_factory()
    resp = _pitch(client, ctx["game_id"], ctx["headers"], pitch_type="IBB")
    assert resp.status_code == 200


# ---------------------------------------------------------------- swing ---


def test_swing_feliz_resuelve_y_cpu_pichea(client, game_factory, mutate_game, broadcasts):
    ctx = game_factory()
    mutate_game(ctx["game_id"], columns={"is_top_inning": False}, state=_bottom_state(ctx))
    resp = _swing(client, ctx["game_id"], ctx["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["event"]
    assert body["description"]
    assert "state_data" in body

    captured = broadcasts[ctx["game_id"]]
    types = [m["message"]["type"] for m in captured]
    assert "PLAY_RESOLVED" in types
    assert "PITCH_COMMITTED" in types
    play = next(m for m in captured if m["message"]["type"] == "PLAY_RESOLVED")
    assert play["channel"] == "to_game_view"


def test_swing_fuera_de_turno_top_403(client, game_factory):
    ctx = game_factory()
    resp = _swing(client, ctx["game_id"], ctx["headers"])
    assert resp.status_code == 403


def test_swing_bloqueado_por_cambio_pendiente_403(client, game_factory, mutate_game):
    ctx = game_factory()
    mutate_game(
        ctx["game_id"],
        columns={"is_top_inning": False},
        state={**_bottom_state(ctx), "awaiting_pitcher_change_acknowledgment": True},
    )
    resp = _swing(client, ctx["game_id"], ctx["headers"])
    assert resp.status_code == 403


def test_swing_persiste_resultado_en_estado(client, game_factory, mutate_game, seed_session):
    ctx = game_factory()
    mutate_game(ctx["game_id"], columns={"is_top_inning": False}, state=_bottom_state(ctx))
    resp = _swing(client, ctx["game_id"], ctx["headers"])
    assert resp.status_code == 200

    from app.models import GameSession

    game = seed_session.query(GameSession).filter(GameSession.id == ctx["game_id"]).one()
    assert "current_pitch" in (game.state_data or {})


# ---------------------------------------------------------------- steal ---


def test_steal_con_corredor_en_primera(client, game_factory, mutate_game, broadcasts):
    ctx = game_factory()
    lineup = ctx["roster"]["lineup"]
    mutate_game(
        ctx["game_id"],
        state={"runners": {"1b": lineup[1], "2b": None, "3b": None}},
    )
    resp = client.post(
        f"/api/v1/games/{ctx['game_id']}/steal",
        json={"target_base": "2b"},
        headers=ctx["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert isinstance(body["success"], bool)
    assert body["description"]

    captured = broadcasts[ctx["game_id"]]
    types = [m["message"]["type"] for m in captured]
    assert "STEAL_RESOLVED" in types


def test_steal_sin_corredor_devuelve_error_descripcion(client, game_factory):
    ctx = game_factory()
    resp = client.post(
        f"/api/v1/games/{ctx['game_id']}/steal",
        json={"target_base": "2b"},
        headers=ctx["headers"],
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["success"], bool)


def test_steal_ajena_403(client, game_factory, register_user):
    ctx = game_factory()
    outsider = register_user("ct_steal403")
    resp = client.post(
        f"/api/v1/games/{ctx['game_id']}/steal",
        json={"target_base": "2b"},
        headers={"Authorization": f"Bearer {outsider['token']}"},
    )
    assert resp.status_code == 403


# ---------------------------------------------------------- change pitcher ---


def _active_pitcher_id(game_id, seed_session):
    from app.models import GameSession

    return (seed_session.query(GameSession).filter(GameSession.id == game_id).one().state_data or {}).get("active_pitcher")


def test_change_pitcher_feliz(client, game_factory, mutate_game, seed_session, broadcasts):
    ctx = game_factory(extra_human_pitchers=1)
    reliever = ctx["roster"]["pitchers"][1]
    active = _active_pitcher_id(ctx["game_id"], seed_session)
    mutate_game(
        ctx["game_id"],
        state={"pitch_counts": {active: MIN_PITCHES_TO_CHANGE}},
    )
    seed_session.commit()

    resp = _change_pitcher(client, ctx["game_id"], ctx["headers"], reliever)
    assert resp.status_code == 200
    body = resp.json()
    assert body["active_pitcher_id"] == reliever

    captured = broadcasts[ctx["game_id"]]
    types = [m["message"]["type"] for m in captured]
    assert "PITCHER_CHANGED" in types
    changed = next(m for m in captured if m["message"]["type"] == "PITCHER_CHANGED")
    assert changed["message"]["new_pitcher_id"] == reliever


def test_change_pitcher_sin_inventario_400(client, game_factory, mutate_game, seed_session):
    ctx = game_factory()
    reliever = ctx["roster"]["pitchers"][1]
    active = _active_pitcher_id(ctx["game_id"], seed_session)
    mutate_game(ctx["game_id"], state={"pitch_counts": {active: MIN_PITCHES_TO_CHANGE}})
    resp = _change_pitcher(client, ctx["game_id"], ctx["headers"], reliever)
    assert resp.status_code == 400
    assert "inventario" in resp.json()["detail"]


def test_change_pitcher_pendiente_conflicto_409(client, game_factory, mutate_game):
    ctx = game_factory()
    mutate_game(ctx["game_id"], state={"awaiting_pitcher_change_acknowledgment": True})
    resp = _change_pitcher(
        client, ctx["game_id"], ctx["headers"], ctx["roster"]["pitchers"][1]
    )
    assert resp.status_code == 409


def test_change_pitcher_fuera_de_turno_403(client, game_factory, mutate_game):
    ctx = game_factory()
    mutate_game(ctx["game_id"], columns={"is_top_inning": False}, state=_bottom_state(ctx))
    resp = _change_pitcher(
        client, ctx["game_id"], ctx["headers"], ctx["roster"]["pitchers"][1]
    )
    assert resp.status_code == 403


def test_change_pitcher_ya_activo_400(client, game_factory, mutate_game, seed_session):
    ctx = game_factory()
    active = _active_pitcher_id(ctx["game_id"], seed_session)
    from app.models import UserCardInventory

    seed_session.add(UserCardInventory(user_id=ctx["me"]["user_id"], card_id=active))
    mutate_game(ctx["game_id"], state={"pitch_counts": {active: MIN_PITCHES_TO_CHANGE}})
    seed_session.commit()
    resp = _change_pitcher(client, ctx["game_id"], ctx["headers"], active)
    assert resp.status_code == 400


# ------------------------------------------------------------ bullpen lists ---


def test_bullpen_usuario_y_rival(client, game_factory):
    ctx = game_factory()
    resp_user = client.get(
        f"/api/v1/games/{ctx['game_id']}/available-pitchers",
        headers=ctx["headers"],
    )
    assert resp_user.status_code == 200
    assert resp_user.json()["status"] == "ok"

    resp_rival = client.get(
        f"/api/v1/games/{ctx['game_id']}/rival-available-pitchers",
        headers=ctx["headers"],
    )
    assert resp_rival.status_code == 200
    assert resp_rival.json()["status"] == "ok"
    assert resp_rival.json()["count"] >= 1


def test_bullpen_rival_no_enumera_pitcher_fuera_del_snapshot(
    client,
    register_user,
    seed_session,
):
    from app.models import UserCardInventory
    from tests.fixtures import seed_versioned_cpu_roster

    cpu = seed_versioned_cpu_roster(seed_session)
    me = register_user("ct_cpu_bullpen_snapshot")
    active_cards = cpu["active_cards"]
    human_lineup = [card.id for card in active_cards if card.is_batter][:9]
    # El CPU usa esta misma política para elegir su starter. Así el pitcher
    # activo inicial no colisiona con el relevista que queda en away_bullpen.
    human_pitcher = sorted(
        (card for card in active_cards if card.is_pitcher),
        key=lambda card: (-card.overall, card.id),
    )[0].id

    for card_id in [*human_lineup, human_pitcher]:
        seed_session.add(
            UserCardInventory(user_id=me["user_id"], card_id=card_id)
        )
    seed_session.commit()

    created = client.post(
        "/api/v1/games/create",
        json={
            "home_user_id": me["user_id"],
            "away_user_id": cpu["team"].id,
            "game_mode": "PVE",
            "difficulty": "MEDIUM",
            "total_innings": 9,
            "player_position": "HOME",
            "home_pitcher_id": human_pitcher,
            "home_lineup": human_lineup,
            "home_tactics_deck": ["t1"],
            "away_tactics_deck": ["t1"],
        },
        headers={"Authorization": f"Bearer {me['token']}"},
    )
    assert created.status_code == 201

    game = created.json()
    cpu_bullpen = game["state_data"]["away_bullpen"]
    retired_pitcher = next(
        card.id for card in cpu["retired_cards"] if card.is_pitcher
    )
    assert retired_pitcher not in cpu_bullpen

    resp = client.get(
        f"/api/v1/games/{game['id']}/rival-available-pitchers",
        headers={"Authorization": f"Bearer {me['token']}"},
    )

    assert resp.status_code == 200
    rival_ids = {
        pitcher["id"]
        for pitcher in resp.json()["available_pitchers"]
    }
    assert rival_ids == set(cpu_bullpen)
    assert retired_pitcher not in rival_ids


def test_cambio_cpu_no_selecciona_pitcher_fuera_del_snapshot(
    client,
    register_user,
    seed_session,
    broadcasts,
):
    import asyncio

    from app.engine.game_actions import execute_cpu_pitcher_change
    from app.models import GameSession, UserCardInventory
    from tests.fixtures import seed_versioned_cpu_roster

    cpu = seed_versioned_cpu_roster(seed_session)
    me = register_user("ct_cpu_change_snapshot")
    active_cards = cpu["active_cards"]
    human_lineup = [card.id for card in active_cards if card.is_batter][:9]
    human_pitcher = sorted(
        (card for card in active_cards if card.is_pitcher),
        key=lambda card: (-card.overall, card.id),
    )[0].id

    for card_id in [*human_lineup, human_pitcher]:
        seed_session.add(
            UserCardInventory(user_id=me["user_id"], card_id=card_id)
        )
    seed_session.commit()

    created = client.post(
        "/api/v1/games/create",
        json={
            "home_user_id": me["user_id"],
            "away_user_id": cpu["team"].id,
            "game_mode": "PVE",
            "difficulty": "MEDIUM",
            "total_innings": 9,
            "player_position": "HOME",
            "home_pitcher_id": human_pitcher,
            "home_lineup": human_lineup,
            "home_tactics_deck": ["t1"],
            "away_tactics_deck": ["t1"],
        },
        headers={"Authorization": f"Bearer {me['token']}"},
    )
    assert created.status_code == 201

    game = seed_session.get(GameSession, created.json()["id"])
    state = dict(game.state_data or {})
    cpu_bullpen = set(state["away_bullpen"])
    retired_pitcher = next(
        card for card in cpu["retired_cards"] if card.is_pitcher
    )
    assert retired_pitcher.id not in cpu_bullpen

    # Si el motor consulta el equipo global, este pitcher histórico gana por OVR.
    retired_pitcher.overall = 99
    seed_session.commit()

    changed = asyncio.run(
        execute_cpu_pitcher_change(
            game,
            state,
            seed_session,
            game.id,
            "MEDIUM",
        )
    )

    assert changed is True
    assert state["away_pitcher_id"] in cpu_bullpen
    assert state["away_pitcher_id"] != retired_pitcher.id


def test_bullpen_usuario_no_enumera_pitcher_adquirido_despues_de_crear_partida(
    client,
    game_factory,
    seed_session,
):
    ctx = game_factory()
    late_pitcher = ctx["roster"]["pitchers"][1]

    from app.models import UserCardInventory

    # T1: adquirido después de crear la partida.
    seed_session.add(
        UserCardInventory(
            user_id=ctx["me"]["user_id"],
            card_id=late_pitcher,
        )
    )
    seed_session.commit()

    resp = client.get(
        f"/api/v1/games/{ctx['game_id']}/available-pitchers",
        headers=ctx["headers"],
    )

    assert resp.status_code == 200
    available_ids = {
        pitcher["id"]
        for pitcher in resp.json()["available_pitchers"]
    }

    assert late_pitcher not in available_ids


def test_cambio_pitcher_usuario_rechaza_pitcher_adquirido_despues_de_crear_partida(
    client,
    game_factory,
    mutate_game,
    seed_session,
):
    ctx = game_factory()
    late_pitcher = ctx["roster"]["pitchers"][1]
    active_pitcher = _active_pitcher_id(ctx["game_id"], seed_session)

    from app.models import UserCardInventory

    # T1: adquirido después de crear la partida.
    seed_session.add(
        UserCardInventory(
            user_id=ctx["me"]["user_id"],
            card_id=late_pitcher,
        )
    )
    mutate_game(
        ctx["game_id"],
        state={"pitch_counts": {active_pitcher: MIN_PITCHES_TO_CHANGE}},
    )
    seed_session.commit()

    resp = _change_pitcher(
        client,
        ctx["game_id"],
        ctx["headers"],
        late_pitcher,
    )

    assert resp.status_code == 400


def test_bullpen_ajena_403(client, game_factory, register_user):
    ctx = game_factory()
    outsider = register_user("ct_bull403")
    headers = {"Authorization": f"Bearer {outsider['token']}"}
    for endpoint in ("available-pitchers", "rival-available-pitchers"):
        resp = client.get(f"/api/v1/games/{ctx['game_id']}/{endpoint}", headers=headers)
        assert resp.status_code == 403


def test_bullpen_partida_inexistente_404(client, game_factory):
    headers = game_factory()["headers"]
    resp = client.get(
        "/api/v1/games/no-existe-partida/available-pitchers",
        headers=headers,
    )
    assert resp.status_code == 404


# ------------------------------------------------------ acknowledge change ---


def test_acknowledge_sin_cambio_pendiente_ok(client, game_factory):
    ctx = game_factory()
    resp = client.post(
        f"/api/v1/games/{ctx['game_id']}/acknowledge-pitcher-change",
        headers=ctx["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_acknowledge_desbloquea_y_broadcast(client, game_factory, mutate_game, broadcasts):
    ctx = game_factory()
    mutate_game(
        ctx["game_id"],
        state={
            "awaiting_pitcher_change_acknowledgment": True,
            "pending_pitcher_change": {"old_pitcher_id": "x", "new_pitcher_id": "y"},
        },
    )
    resp = client.post(
        f"/api/v1/games/{ctx['game_id']}/acknowledge-pitcher-change",
        headers=ctx["headers"],
    )
    assert resp.status_code == 200
    captured = broadcasts[ctx["game_id"]]
    types = [m["message"]["type"] for m in captured]
    assert "PITCHER_CHANGE_ACKNOWLEDGED" in types


# ---------------------------------------------------------------- tactics ---


def _seed_tactic_card(seed_session, tactic_id, category="BUFF"):
    from app.models import TacticCard

    if not seed_session.query(TacticCard).filter(TacticCard.id == tactic_id).first():
        seed_session.add(
            TacticCard(
                id=tactic_id,
                name=f"Tactic {tactic_id}",
                category=category,
                target_role="PITCHER",
                effects={},
                description="tactic de contrato",
            )
        )
        seed_session.commit()


def test_play_tactic_feliz_en_mano(client, game_factory, mutate_game, seed_session):
    ctx = game_factory()
    _seed_tactic_card(seed_session, "t1")
    mutate_game(
        ctx["game_id"],
        state={"tactics": {"home": {"deck": [], "hand": ["t1"], "discard": []}}},
    )
    resp = client.post(
        f"/api/v1/games/{ctx['game_id']}/play-tactic",
        json={"player_role": "PITCHER", "tactic_id": "t1"},
        headers=ctx["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert "t1" in resp.json()["message"]


def test_play_tactic_fuera_de_mano_400(client, game_factory, mutate_game, seed_session):
    ctx = game_factory()
    _seed_tactic_card(seed_session, "t9")
    mutate_game(
        ctx["game_id"],
        state={"tactics": {"home": {"deck": [], "hand": ["t1"], "discard": []}}},
    )
    resp = client.post(
        f"/api/v1/games/{ctx['game_id']}/play-tactic",
        json={"player_role": "PITCHER", "tactic_id": "t9"},
        headers=ctx["headers"],
    )
    assert resp.status_code == 400


def test_play_tactic_desconocida_404(client, game_factory, mutate_game):
    ctx = game_factory()
    mutate_game(
        ctx["game_id"],
        state={"tactics": {"home": {"deck": [], "hand": ["zz"], "discard": []}}},
    )
    resp = client.post(
        f"/api/v1/games/{ctx['game_id']}/play-tactic",
        json={"player_role": "PITCHER", "tactic_id": "zz"},
        headers=ctx["headers"],
    )
    assert resp.status_code == 404


def test_play_tactic_extra_innings_bajo_10_400(client, game_factory, mutate_game, seed_session):
    ctx = game_factory()
    _seed_tactic_card(seed_session, "t10", category="EXTRA_INNINGS")
    mutate_game(
        ctx["game_id"],
        columns={"current_inning": 1},
        state={"tactics": {"home": {"deck": [], "hand": ["t10"], "discard": []}}},
    )
    resp = client.post(
        f"/api/v1/games/{ctx['game_id']}/play-tactic",
        json={"player_role": "PITCHER", "tactic_id": "t10"},
        headers=ctx["headers"],
    )
    assert resp.status_code == 400
    assert "extra innings" in resp.json()["detail"]


def test_play_tactic_rol_invalido_400(client, game_factory, mutate_game, seed_session):
    ctx = game_factory()
    _seed_tactic_card(seed_session, "t1")
    mutate_game(
        ctx["game_id"],
        state={"tactics": {"home": {"deck": [], "hand": ["t1"], "discard": []}}},
    )
    resp = client.post(
        f"/api/v1/games/{ctx['game_id']}/play-tactic",
        json={"player_role": "COACH", "tactic_id": "t1"},
        headers=ctx["headers"],
    )
    assert resp.status_code == 400


def test_play_tactic_ajena_403(client, game_factory, mutate_game, register_user):
    ctx = game_factory()
    mutate_game(
        ctx["game_id"],
        state={"tactics": {"home": {"deck": [], "hand": ["t1"], "discard": []}}},
    )
    outsider = register_user("ct_tac403")
    resp = client.post(
        f"/api/v1/games/{ctx['game_id']}/play-tactic",
        json={"player_role": "PITCHER", "tactic_id": "t1"},
        headers={"Authorization": f"Bearer {outsider['token']}"},
    )
    assert resp.status_code == 403
