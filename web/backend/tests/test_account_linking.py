"""Telegram and username/password are two independent ways into the same
account — this covers linking them in both directions, and the collision
guard when a Telegram id is already claimed by someone else."""

import time
import uuid

from fastapi.testclient import TestClient

from app.main import app
from app.routers import telegram_auth as telegram_auth_router


def _unique(name: str) -> str:
    return f"{name}_{uuid.uuid4().hex[:8]}"


def _telegram_payload(telegram_id: int, **overrides) -> dict:
    payload = {
        "id": telegram_id,
        "first_name": "Ada",
        "username": "ada_tg",
        "auth_date": int(time.time()),
        "hash": "irrelevant-because-verify-is-monkeypatched",
    }
    payload.update(overrides)
    return payload


def test_password_user_can_link_telegram(monkeypatch):
    monkeypatch.setattr(telegram_auth_router.telegram_auth, "verify_telegram_login", lambda data: data)
    client = TestClient(app)

    username = _unique("linker")
    signup = client.post("/api/auth/signup", json={"username": username, "password": "some password here"})
    assert signup.status_code == 200
    assert signup.json()["telegram_linked"] is False

    telegram_id = int(uuid.uuid4().int % 10**9)
    link_resp = client.post("/api/auth/telegram/link", json=_telegram_payload(telegram_id))
    assert link_resp.status_code == 200, link_resp.text
    body = link_resp.json()
    assert body["telegram_linked"] is True
    assert body["telegram_id"] == telegram_id
    assert body["username"] == username  # still the same account, password login intact


def test_telegram_user_can_set_password(monkeypatch):
    monkeypatch.setattr(telegram_auth_router.telegram_auth, "verify_telegram_login", lambda data: data)
    client = TestClient(app)

    telegram_id = int(uuid.uuid4().int % 10**9)
    callback = client.post("/api/auth/telegram/callback", json=_telegram_payload(telegram_id))
    assert callback.status_code == 200
    assert callback.json()["has_password"] is False

    username = _unique("setpw")
    set_pw = client.post("/api/auth/set-password", json={"username": username, "password": "brand new password"})
    assert set_pw.status_code == 200, set_pw.text
    assert "recovery_code" in set_pw.json()

    # Can now log in with the password too, on a totally fresh client.
    login = TestClient(app).post("/api/auth/login", json={"username": username, "password": "brand new password"})
    assert login.status_code == 200
    assert login.json()["telegram_id"] == telegram_id  # same underlying account


def test_linking_telegram_already_claimed_by_another_account_is_rejected(monkeypatch):
    monkeypatch.setattr(telegram_auth_router.telegram_auth, "verify_telegram_login", lambda data: data)
    telegram_id = int(uuid.uuid4().int % 10**9)

    owner_client = TestClient(app)
    owner_client.post("/api/auth/telegram/callback", json=_telegram_payload(telegram_id))

    other_client = TestClient(app)
    other_client.post("/api/auth/signup", json={"username": _unique("other"), "password": "some password"})
    resp = other_client.post("/api/auth/telegram/link", json=_telegram_payload(telegram_id))
    assert resp.status_code == 409
