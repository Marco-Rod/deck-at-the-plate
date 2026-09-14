"""Contract tests del router de sesión de juego (create/get/box-score/stats)."""

from __future__ import annotations

import pytest


def _ban(me: dict) -> dict:
    return {"Authorization": f"Bearer {me['token']}"}


def _payload(me: dict, roster: dict, **overrides) -> dict:
    payload = {
        "home_user_id": me["user_id"],
        "away_user_id": roster["team"].id,
        "game_mode": "PVE",
        "difficulty": "MEDIUM",
        "total_innings": 9,
        "player_position": "HOME",
        "home_pitcher_id": roster["pitchers"][0],
        "home_lineup": roster["lineup"][:9],
        "home_tactics_deck": ["t1", "t2", "t3", "t4", "t1"],
        "away_tactics_deck": ["t1", "t2", "t3", "t4", "t1"],
    }
    payload.update(overrides)
    return payload


def _create(client, payload, headers=None):
    return client.post("/api/v1/games/create", json=payload, headers=headers)


def test_crear_sesion_feliz(client, game_factory):
    ctx = game_factory()
    resp = client.get(f"/api/v1/games/{ctx['game_id']}", headers=ctx["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == ctx["game_id"]
    assert body["is_top_inning"] is True
    assert body["state_data"]["user_role"] == "HOME"
    assert body["state_data"]["active_pitcher"]


def test_crear_en_nombre_de_otro_usuario_403(client, register_user, roster_factory):
    roster = roster_factory()
    me = register_user("ct_owner")
    other = register_user("ct_intruder")
    resp = _create(
        client,
        {**_payload(me, roster), "home_user_id": other["user_id"]},
        headers=_ban(me),
    )
    assert resp.status_code == 403
    assert "otro usuario" in resp.json()["detail"]


def test_crear_sin_token_401(client, roster_factory):
    resp = _create(client, _payload({"user_id": "x", "token": ""}, roster_factory()))
    assert resp.status_code == 401


@pytest.mark.parametrize("player_position", ["SIDELINE", "DUGOUT"])
def test_crear_player_position_invalida_400(client, game_factory, player_position):
    ctx = game_factory()
    resp = _create(
        client,
        _payload(ctx["me"], ctx["roster"], player_position=player_position),
        headers=ctx["headers"],
    )
    assert resp.status_code == 400


def test_crear_equipo_cpu_sin_cartas_error(client, register_user):
    me = register_user("ct_noroam")
    payload = {
        "home_user_id": me["user_id"],
        "away_user_id": "3f0c1133-6f5f-4a2a-9d2f-0a1b2c3d4e5f",
        "game_mode": "PVE",
        "player_position": "HOME",
        "home_lineup": [],
        "home_tactics_deck": ["t1"],
        "away_tactics_deck": ["t1"],
    }
    resp = _create(client, payload, headers=_ban(me))
    assert resp.status_code == 500


def test_get_sesion_no_encontrada_404(client, register_user):
    me = register_user("ct_g404")
    resp = client.get(
        "/api/v1/games/no-existe-esta-partida",
        headers=_ban(me),
    )
    assert resp.status_code == 404


def test_get_sesion_ajena_403(client, game_factory, register_user):
    ctx = game_factory()
    outsider = register_user("ct_outsider")
    resp = client.get(
        f"/api/v1/games/{ctx['game_id']}",
        headers=_ban(outsider),
    )
    assert resp.status_code == 403


def test_fog_of_war_no_expone_picheo_del_rival(client, game_factory, mutate_game):
    ctx = game_factory()
    # El humano (HOME) pichea en la Alta; para ver el picheo del rival (CPU) debe
    # estar en la Baja, donde es el bateador.
    mutate_game(
        ctx["game_id"],
        columns={"is_top_inning": False},
        state={"current_pitch": {"pitch_type": "FF", "zone": 5}},
    )
    resp = client.get(
        f"/api/v1/games/{ctx['game_id']}",
        headers=ctx["headers"],
    )
    assert resp.status_code == 200
    state = resp.json()["state_data"]
    masked = state["current_pitch"]
    assert masked["has_pitched"] is True
    assert masked["pitch_type"] is None
    assert masked["zone"] is None


def test_box_score_partida_nueva(client, game_factory):
    ctx = game_factory()
    resp = client.get(
        f"/api/v1/games/{ctx['game_id']}/box-score",
        headers=ctx["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["game_id"] == ctx["game_id"]
    assert body["final_score"]["home"] == 0
    assert body["final_score"]["away"] == 0
    assert "box_score" in body


def test_box_score_ajena_403(client, game_factory, register_user):
    ctx = game_factory()
    outsider = register_user("ct_bs403")
    resp = client.get(
        f"/api/v1/games/{ctx['game_id']}/box-score",
        headers=_ban(outsider),
    )
    assert resp.status_code == 403


def test_stats_bateador_en_partida(client, game_factory):
    ctx = game_factory()
    batter_id = ctx["roster"]["lineup"][0]
    resp = client.get(
        f"/api/v1/games/{ctx['game_id']}/player/{batter_id}/stats",
        headers=ctx["headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["player_id"] == batter_id


def test_get_sesion_es_la_creada(client, game_factory):
    ctx = game_factory()
    resp = client.get(f"/api/v1/games/{ctx['game_id']}", headers=ctx["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["home_user_id"] == ctx["me"]["user_id"]
    # En PvE la sesión normaliza el lado rival al marcador de CPU.
    assert body["away_user_id"] == "CPU_BOT"


def test_crear_responde_201_y_campos_minimos(client, game_factory):
    ctx = game_factory()
    created = client.post(
        "/api/v1/games/create",
        json=_payload(ctx["me"], ctx["roster"]),
        headers=ctx["headers"],
    )
    assert created.status_code == 201
    body = created.json()
    for key in ("id", "home_user_id", "away_user_id", "current_inning", "is_top_inning", "outs", "balls", "strikes", "score_home", "score_away"):
        assert key in body