"""Pruebas del ExternalHttpClient con transport mockeado (spec §6/§48)."""

import pytest
import httpx

from etl.http.client import ExternalHttpClient


def _client_with(handler, **kwargs):
    transport = httpx.MockTransport(handler)
    return ExternalHttpClient(transport=transport, retry_backoff=(0, 0, 0), **kwargs)


def test_retry_transitorio_hasta_200():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    client = _client_with(handler)
    response = client.get("https://example.com/api")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert calls["n"] == 3


def test_no_retry_en_error_funcional_404():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(404, request=request)

    client = _client_with(handler)
    response = client.get("https://example.com/missing")
    assert response.status_code == 404
    assert calls["n"] == 1


def test_no_retry_en_400():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(400, request=request)

    client = _client_with(handler)
    response = client.get("https://example.com/bad")
    assert response.status_code == 400
    assert calls["n"] == 1


def test_retries_agotadas_lanza_tras_error_permanente():
    def handler(request):
        return httpx.Response(503, request=request)

    client = _client_with(handler, max_retries=2)
    with pytest.raises(httpx.HTTPStatusError):
        client.get("https://example.com/always-down")


def test_429_es_reintentable():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, request=request)
        return httpx.Response(200, request=request)

    client = _client_with(handler)
    response = client.get("https://example.com/rate-limited")
    assert response.status_code == 200
    assert calls["n"] == 2


def test_user_agent_configurable():
    seen = {}

    def handler(request):
        seen["ua"] = request.headers.get("User-Agent")
        return httpx.Response(200, request=request)

    client = ExternalHttpClient(transport=httpx.MockTransport(handler), user_agent="DeckAtThePlate-ETL/test")
    client.get("https://example.com")
    assert seen["ua"] == "DeckAtThePlate-ETL/test"