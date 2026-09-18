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


def test_crear_rechaza_bateador_que_usuario_no_posee(
    client,
    register_user,
    roster_factory,
    seed_session,
):
    from app.models import UserCardInventory

    roster = roster_factory()
    me = register_user("ownership_batter_test")
    owned_batters = roster["lineup"][:8]
    unowned_batter = roster["lineup"][8]
    pitcher_id = roster["pitchers"][0]

    for card_id in [*owned_batters, pitcher_id]:
        seed_session.add(
            UserCardInventory(user_id=me["user_id"], card_id=card_id)
        )
    seed_session.commit()

    resp = _create(
        client,
        _payload(
            me,
            roster,
            home_pitcher_id=pitcher_id,
            home_lineup=[*owned_batters, unowned_batter],
        ),
        headers=_ban(me),
    )

    assert resp.status_code in (400, 403)


def test_crear_rechaza_pitcher_que_usuario_no_posee(
    client,
    register_user,
    roster_factory,
    seed_session,
):
    from app.models import UserCardInventory

    roster = roster_factory()
    me = register_user("ownership_pitcher_test")
    lineup = roster["lineup"][:9]
    owned_pitcher = roster["pitchers"][0]
    unowned_pitcher = roster["pitchers"][1]

    for card_id in [*lineup, owned_pitcher]:
        seed_session.add(
            UserCardInventory(user_id=me["user_id"], card_id=card_id)
        )
    seed_session.commit()

    resp = _create(
        client,
        _payload(
            me,
            roster,
            home_pitcher_id=unowned_pitcher,
            home_lineup=lineup,
        ),
        headers=_ban(me),
    )

    assert resp.status_code in (400, 403)


def test_crear_rechaza_lineup_con_bateadores_duplicados(
    client,
    register_user,
    roster_factory,
    seed_session,
):
    from app.models import UserCardInventory

    roster = roster_factory()
    me = register_user("duplicate_batter_test")
    lineup = roster["lineup"][:9]
    pitcher_id = roster["pitchers"][0]
    for card_id in [*lineup, pitcher_id]:
        seed_session.add(
            UserCardInventory(user_id=me["user_id"], card_id=card_id)
        )
    seed_session.commit()

    duplicated_lineup = [*lineup[:8], lineup[0]]
    resp = _create(
        client,
        _payload(
            me,
            roster,
            home_pitcher_id=pitcher_id,
            home_lineup=duplicated_lineup,
        ),
        headers=_ban(me),
    )

    assert resp.status_code == 400


def test_crear_rechaza_pitcher_usado_como_bateador(
    client,
    register_user,
    roster_factory,
    seed_session,
):
    from app.models import UserCardInventory

    roster = roster_factory()
    me = register_user("pitcher_as_batter_test")
    lineup = roster["lineup"][:9]
    pitcher_id = roster["pitchers"][0]
    second_pitcher_id = roster["pitchers"][1]
    for card_id in [*lineup, pitcher_id, second_pitcher_id]:
        seed_session.add(
            UserCardInventory(user_id=me["user_id"], card_id=card_id)
        )
    seed_session.commit()

    invalid_lineup = [*lineup[:8], second_pitcher_id]
    resp = _create(
        client,
        _payload(
            me,
            roster,
            home_pitcher_id=pitcher_id,
            home_lineup=invalid_lineup,
        ),
        headers=_ban(me),
    )

    assert resp.status_code == 400


def test_crear_rechaza_bateador_usado_como_pitcher(
    client,
    register_user,
    roster_factory,
    seed_session,
):
    from app.models import UserCardInventory

    roster = roster_factory()
    me = register_user("batter_as_pitcher_test")
    lineup = roster["lineup"][:9]
    invalid_pitcher_id = lineup[0]
    for card_id in lineup:
        seed_session.add(
            UserCardInventory(user_id=me["user_id"], card_id=card_id)
        )
    seed_session.commit()

    resp = _create(
        client,
        _payload(
            me,
            roster,
            home_pitcher_id=invalid_pitcher_id,
            home_lineup=lineup,
        ),
        headers=_ban(me),
    )

    assert resp.status_code == 400


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


def test_crear_rechaza_equipo_cpu_sin_cartas_400(
    client,
    register_user,
    roster_factory,
    seed_session,
):
    import uuid

    from app.models import Team, UserCardInventory

    roster = roster_factory()
    me = register_user("ct_noroam")
    human_lineup = roster["lineup"][:9]
    human_pitcher = roster["pitchers"][0]
    for card_id in [*human_lineup, human_pitcher]:
        seed_session.add(
            UserCardInventory(user_id=me["user_id"], card_id=card_id)
        )

    empty_cpu_team = Team(
        id=str(uuid.uuid4()),
        abbreviation="EMPTY",
        name="Empty CPU Team",
        city="Test City",
    )
    seed_session.add(empty_cpu_team)
    seed_session.commit()

    payload = {
        "home_user_id": me["user_id"],
        "away_user_id": empty_cpu_team.id,
        "game_mode": "PVE",
        "player_position": "HOME",
        "home_pitcher_id": human_pitcher,
        "home_lineup": human_lineup,
        "home_tactics_deck": ["t1"],
        "away_tactics_deck": ["t1"],
    }
    resp = _create(client, payload, headers=_ban(me))
    assert resp.status_code == 400
    assert resp.json()["detail"] == "El equipo CPU seleccionado no tiene cartas disponibles"


def test_crear_cpu_usa_solo_cartas_del_catalogo_activo(
    client,
    register_user,
    seed_session,
):
    from app.models import UserCardInventory
    from tests.fixtures import seed_versioned_cpu_roster

    cpu = seed_versioned_cpu_roster(
        seed_session,
        team_id="5f0c1133-6f5f-4a2a-9d2f-0a1b2c3d4e7f",
    )
    me = register_user("ct_cpu_catalog")
    active_cards = cpu["active_cards"]
    human_batters = [card for card in active_cards if card.is_batter][:9]
    human_pitchers = [card for card in active_cards if card.is_pitcher]
    assert len(human_batters) == 9
    assert human_pitchers
    human_lineup = [card.id for card in human_batters]
    human_pitcher = human_pitchers[0].id
    for card_id in [*human_lineup, human_pitcher]:
        seed_session.add(
            UserCardInventory(user_id=me["user_id"], card_id=card_id)
        )
    seed_session.commit()

    payload = {
        "home_user_id": me["user_id"],
        "away_user_id": cpu["team"].id,
        "game_mode": "PVE",
        "player_position": "HOME",
        "home_pitcher_id": human_pitcher,
        "home_lineup": human_lineup,
        "home_tactics_deck": ["t1"],
        "away_tactics_deck": ["t1"],
    }

    resp = _create(client, payload, headers=_ban(me))

    assert resp.status_code == 201
    state = resp.json()["state_data"]
    cpu_card_ids = {*state["away_lineup"], state["away_pitcher_id"]}
    retired_ids = {card.id for card in cpu["retired_cards"]}
    active_ids = {card.id for card in cpu["active_cards"]}

    assert cpu_card_ids
    assert cpu_card_ids.isdisjoint(retired_ids)
    assert cpu_card_ids <= active_ids


def test_crear_rechaza_cpu_con_menos_de_nueve_bateadores(
    client,
    register_user,
    seed_session,
):
    from app.models import UserCardInventory
    from tests.fixtures import seed_incomplete_cpu_roster

    seeded = seed_incomplete_cpu_roster(seed_session)
    me = register_user("ct_cpu_short")
    human_batters = [card for card in seeded["human_cards"] if card.is_batter]
    human_pitchers = [card for card in seeded["human_cards"] if card.is_pitcher]
    assert len(human_batters) == 9
    assert human_pitchers
    human_lineup = [card.id for card in human_batters]
    human_pitcher = human_pitchers[0].id
    for card_id in [*human_lineup, human_pitcher]:
        seed_session.add(
            UserCardInventory(user_id=me["user_id"], card_id=card_id)
        )
    seed_session.commit()

    payload = {
        "home_user_id": me["user_id"],
        "away_user_id": seeded["cpu_team"].id,
        "game_mode": "PVE",
        "player_position": "HOME",
        "home_pitcher_id": human_pitcher,
        "home_lineup": human_lineup,
        "home_tactics_deck": ["t1"],
        "away_tactics_deck": ["t1"],
    }
    resp = _create(client, payload, headers=_ban(me))

    assert resp.status_code == 400
    assert resp.json()["detail"] == (
        "El equipo CPU seleccionado no tiene suficientes bateadores"
    )


def test_crear_cpu_selecciona_roster_inicial_deterministicamente(
    client,
    register_user,
    seed_session,
):
    from app.models import UserCardInventory
    from tests.fixtures import seed_incomplete_cpu_roster

    seeded = seed_incomplete_cpu_roster(
        seed_session,
        human_batters=9,
        human_pitchers=1,
        cpu_batters=11,
        cpu_pitchers=3,
    )
    me = register_user("ct_cpu_deterministic")
    human_batters = sorted(
        (card for card in seeded["human_cards"] if card.is_batter),
        key=lambda card: card.id,
    )
    human_pitchers = sorted(
        (card for card in seeded["human_cards"] if card.is_pitcher),
        key=lambda card: card.id,
    )
    human_lineup = [card.id for card in human_batters[:9]]
    human_pitcher = human_pitchers[0].id
    for card_id in [*human_lineup, human_pitcher]:
        seed_session.add(
            UserCardInventory(user_id=me["user_id"], card_id=card_id)
        )
    seed_session.commit()

    cpu_batters = [card for card in seeded["cpu_cards"] if card.is_batter]
    cpu_pitchers = [card for card in seeded["cpu_cards"] if card.is_pitcher]
    expected_lineup = [
        card.id
        for card in sorted(
            cpu_batters,
            key=lambda card: (-card.overall, card.id),
        )[:9]
    ]
    expected_pitcher = sorted(
        cpu_pitchers,
        key=lambda card: (-card.overall, card.id),
    )[0].id

    payload = {
        "home_user_id": me["user_id"],
        "away_user_id": seeded["cpu_team"].id,
        "game_mode": "PVE",
        "player_position": "HOME",
        "home_pitcher_id": human_pitcher,
        "home_lineup": human_lineup,
        "home_tactics_deck": ["t1"],
        "away_tactics_deck": ["t1"],
    }
    resp = _create(client, payload, headers=_ban(me))

    assert resp.status_code == 201
    state = resp.json()["state_data"]
    assert state["away_lineup"] == expected_lineup
    assert state["away_pitcher_id"] == expected_pitcher


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
