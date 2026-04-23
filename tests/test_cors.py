"""CORS middleware tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api import server as server_mod


def test_cors_preflight_for_allowed_origin():
    client = TestClient(server_mod.app)
    r = client.options(
        "/analyze",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_simple_request_echoes_origin():
    client = TestClient(server_mod.app)
    r = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
