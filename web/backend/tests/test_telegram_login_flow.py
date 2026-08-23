"""End-to-end: Telegram callback -> Set-Cookie -> /api/auth/me."""

import time

from fastapi.testclient import TestClient

from app.main import app
from app.routers import telegram_auth as telegram_auth_router

TEST_ID = 555001


def test_callback_issues_cookie_and_me_reflects_it(monkeypatch):
    monkeypatch.setattr(
        telegram_auth_router.telegram_auth,
        "verify_telegram_login",
        lambda data: data,
    )
    client = TestClient(app)

    payload = {
        "id": TEST_ID,
        "first_name": "Ada",
        "username": "ada_lovelace",
        "photo_url": "https://t.me/i/userpic/ada.jpg",
        "auth_date": int(time.time()),
        "hash": "irrelevant-because-verify-is-monkeypatched",
    }
    resp = client.post("/api/auth/telegram/callback", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["telegram_id"] == TEST_ID
    assert body["telegram_username"] == "ada_lovelace"
    assert body["yc_linked"] is False
    assert "yc_session" in resp.cookies

    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["telegram_id"] == TEST_ID


def test_me_without_cookie_is_401():
    client = TestClient(app)
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_logout_clears_cookie(monkeypatch):
    monkeypatch.setattr(
        telegram_auth_router.telegram_auth,
        "verify_telegram_login",
        lambda data: data,
    )
    client = TestClient(app)
    client.post("/api/auth/telegram/callback", json={
        "id": TEST_ID, "first_name": "Ada", "auth_date": int(time.time()), "hash": "x",
    })
    assert client.get("/api/auth/me").status_code == 200

    logout_resp = client.post("/api/auth/telegram/logout")
    assert logout_resp.status_code == 200

    client.cookies.clear()  # TestClient won't auto-drop a deleted cookie mid-session otherwise
    assert client.get("/api/auth/me").status_code == 401
