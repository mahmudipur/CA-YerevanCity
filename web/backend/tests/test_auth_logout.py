"""Logout must clear a user's YC JWT without touching phone/device id."""

from fastapi.testclient import TestClient

from app.main import app


def test_logout_clears_jwt_keeps_phone_and_device(authed_user_factory):
    authed_user_factory(yc_jwt="some.jwt.token", yc_phone_e164="+37455285320", yc_device_id="abc123")
    client = TestClient(app)

    status_before = client.get("/api/auth/status").json()
    assert status_before["authenticated"] is True

    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.json() == {"authenticated": False}

    status_after = client.get("/api/auth/status").json()
    assert status_after["authenticated"] is False
    assert status_after["phone_e164"] == "+37455285320"  # phone preserved for a fast re-login
