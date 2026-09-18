"""Harness de contract tests (Fase 2) sobre la API real con TestClient.

App FastAPI completa con ``get_db`` sobreescrito a SQLite en memoria
(StaticPool → misma conexión para todas las sesiones) y broadcasts WebSocket
capturados en memoria para poder asertar los eventos del contrato WS sin
levantar sockets reales.

El auth se prueba con el flujo real (register → login → Bearer JWT) en
``test_auth_contract``; los demás tests usan esos tokens reales.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(autouse=True)
def _reset_login_rate_limit():
    """El rate limit 429 de auth es global por IP: se resetea por test."""
    import app.routers.auth as auth_module

    auth_module._login_limits.clear()
    yield
    auth_module._login_limits.clear()


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.database import Base

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False)


@pytest.fixture
def seed_session(session_factory):
    """Sesión del tester sobre la MISMA BD que sirve la API (para fixture/setup)."""
    db = session_factory()
    yield db
    db.close()


@pytest.fixture
def client(session_factory):
    from app.database import get_db
    from app.main import app

    def _override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def broadcasts(monkeypatch):
    """Captura los broadcasts WS por game_id en lugar de emitirlos por socket."""
    captured: dict[str, list[dict]] = {}

    async def _broadcast_to_game(game_id, message):
        captured.setdefault(game_id, []).append(
            {"channel": "to_game", "message": dict(message)}
        )

    async def _broadcast_to_game_view(game_id, build_message):
        payload = build_message("__contract_test__")
        if payload is not None:
            captured.setdefault(game_id, []).append(
                {"channel": "to_game_view", "message": dict(payload)}
            )

    from app.engine.websocket_manager import manager

    monkeypatch.setattr(manager, "broadcast_to_game", _broadcast_to_game)
    monkeypatch.setattr(manager, "broadcast_to_game_view", _broadcast_to_game_view)
    return captured


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def register_user(client):
    """Registra + loguea un usuario real y devuelve {user_id, username, token}."""

    def _register(username: str, password: str = "Passw0rd!x") -> dict:
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": username, "password": password},
        )
        assert resp.status_code == 201, f"registro falló: {resp.status_code} {resp.text}"
        created = resp.json()
        login = client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": password},
        )
        assert login.status_code == 200, f"login falló: {login.status_code} {login.text}"
        return {
            "user_id": created["user_id"],
            "username": created["username"],
            "token": login.json()["access_token"],
        }

    return _register


@pytest.fixture
def roster_factory(seed_session):
    """Crea un equipo CPU con rosters publicados (real flow del catálogo)."""
    from tests import fixtures

    def _roster():
        edition = fixtures.ensure_edition(seed_session)
        roster = fixtures.seed_roster(seed_session, edition)
        seed_session.commit()
        return roster

    return _roster


@pytest.fixture
def game_factory(client, register_user, roster_factory, seed_session):
    """Crea una sesión 1v1 PvE (humano=HOME) por API y devuelve contexto."""

    def _game(
        username: str | None = None,
        *,
        extra_human_pitchers: int = 0,
    ):
        from app.models import UserCardInventory

        roster = roster_factory()
        me = register_user(username or f"home_{uuid.uuid4().hex[:6]}")
        human_lineup = roster["lineup"][:9]
        human_pitcher = roster["pitchers"][0]
        human_bullpen = roster["pitchers"][1:1 + extra_human_pitchers]
        for card_id in [*human_lineup, human_pitcher, *human_bullpen]:
            seed_session.add(
                UserCardInventory(user_id=me["user_id"], card_id=card_id)
            )
        seed_session.commit()
        payload = {
            "home_user_id": me["user_id"],
            "away_user_id": roster["team"].id,
            "game_mode": "PVE",
            "difficulty": "MEDIUM",
            "total_innings": 9,
            "player_position": "HOME",
            "home_pitcher_id": human_pitcher,
            "home_lineup": human_lineup,
            "home_tactics_deck": ["t1", "t2", "t3", "t4", "t1"],
            "away_tactics_deck": ["t1", "t2", "t3", "t4", "t1"],
        }
        resp = client.post(
            "/api/v1/games/create",
            json=payload,
            headers=_auth_headers(me["token"]),
        )
        assert resp.status_code == 201, f"create game falló: {resp.status_code} {resp.text}"
        return {
            "game_id": resp.json()["id"],
            "roster": roster,
            "me": me,
            "headers": _auth_headers(me["token"]),
        }

    return _game


@pytest.fixture
def mutate_game(seed_session):
    """Editor de columnas/state_data de una sesión sin pasar por la API."""

    def _mutate(game_id: str, *, columns=None, state: dict) -> dict:
        from app.models import GameSession

        game = seed_session.query(GameSession).filter(GameSession.id == game_id).one()
        game_state = dict(game.state_data or {})
        game_state.update(state)
        game.state_data = game_state
        if columns:
            for key, value in columns.items():
                setattr(game, key, value)
        seed_session.commit()
        seed_session.refresh(game)
        return dict(game.state_data or {})

    return _mutate
