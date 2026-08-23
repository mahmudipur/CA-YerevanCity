"""send-code/verify hit a real third-party OTP API and must be throttled to
prevent using this app as a free OTP-bombing relay against a phone number."""

from fastapi.testclient import TestClient

from app.main import app
from app.routers import auth as auth_router


def test_send_code_is_rate_limited(monkeypatch, authed_user_factory):
    authed_user_factory()
    monkeypatch.setattr(auth_router, "confirm_code", lambda: "000000")
    monkeypatch.setattr(auth_router, "send_code", lambda *a, **k: None)

    client = TestClient(app)
    body = {"phone_local": "55000000", "phone_e164": "+37455000000"}

    statuses = [client.post("/api/auth/send-code", json=body).status_code for _ in range(4)]
    assert statuses[:3] == [200, 200, 200]
    assert statuses[3] == 429
