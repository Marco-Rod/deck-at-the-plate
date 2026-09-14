"""Contract tests del router de autenticación (real JWT flow)."""

from __future__ import annotations

import uuid

import pytest


@pytest.fixture
def unique_username() -> str:
    return f"ct_user_{uuid.uuid4().hex[:10]}"


def _register(client, username, password="Passw0rd!x"):
    return client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )


def _login(client, username, password="Passw0rd!x"):
    return client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )


def test_register_crea_usuario_y_wallet_default(client, seed_session, unique_username):
    resp = _register(client, unique_username)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "created"
    assert data["username"] == unique_username
    assert data["user_id"]

    from app.models import UserWallet

    wallet = (
        seed_session.query(UserWallet)
        .filter(UserWallet.user_id == data["user_id"])
        .one()
    )
    assert wallet.stamps == 1000
    assert wallet.gems == 0


def test_login_retorna_jwt_y_token_type(client, unique_username):
    assert _register(client, unique_username).status_code == 201
    resp = _login(client, unique_username)
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["username"] == unique_username


def test_registro_duplicado_conflicto_409(client, unique_username):
    assert _register(client, unique_username).status_code == 201
    resp = _register(client, unique_username)
    assert resp.status_code == 409
    assert "ya está en uso" in resp.json()["detail"]


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "ab", "password": "Passw0rd!x"},
        {"username": "usuario_valido", "password": "123"},
        {"username": "usuario_valido", "password": "Passw0rd!x", "unexpected": True},
    ],
)
def test_registro_payload_invalido_422(client, payload):
    bad = {k: v for k, v in payload.items() if k != "unexpected"}
    if payload.get("unexpected"):
        bad["has_completed_onboarding"] = "not-a-bool"
    resp = _register(client, bad)
    assert resp.status_code == 422


def test_login_credenciales_incorrectas_401(client, unique_username):
    assert _register(client, unique_username).status_code == 201
    resp = _login(client, unique_username, password="WrongPass1")
    assert resp.status_code == 401


def test_login_usuario_inexistente_401(client):
    resp = _login(client, "no_existe_este_usuario")
    assert resp.status_code == 401


def test_endpoint_protegido_sin_token_401(client):
    resp = client.get("/api/v1/user/me/profile")
    assert resp.status_code == 401


def test_jwt_valido_accede_al_perfil(client, register_user, seed_session):
    me = register_user("ct_perfil_user")
    resp = client.get(
        "/api/v1/user/me/profile",
        headers={"Authorization": f"Bearer {me['token']}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == me["user_id"]
    assert body["wallet"]["stamps"] == 1000