"""Regression test: a CORS preflight (OPTIONS) from an allowed dev/tunnel
origin must succeed, or the browser blocks the real POST before it's ever
sent — this is what broke signin/forgot-password when only the app itself
was reachable same-origin but the app is commonly run with the frontend on
a different port (Vite dev server) or exposed via ngrok."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.parametrize("origin", [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://abcd1234.ngrok-free.app",
    "https://abcd1234.ngrok.app",
])
def test_preflight_succeeds_for_allowed_origins(origin):
    resp = client.options(
        "/api/auth/login",
        headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == origin
    assert resp.headers["access-control-allow-credentials"] == "true"


def test_preflight_rejects_untrusted_origin():
    resp = client.options(
        "/api/auth/login",
        headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in resp.headers


def test_real_post_still_works_with_allowed_origin():
    resp = client.post(
        "/api/auth/login",
        json={"username": "no-such-user", "password": "whatever"},
        headers={"Origin": "http://localhost:5173"},
    )
    assert resp.status_code == 401  # reaches the handler, not blocked/405'd
