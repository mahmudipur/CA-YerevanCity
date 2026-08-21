"""
Logout must clear YC_JWT without touching phone/device id. Uses an in-memory
fake for env_store so the test never writes to the developer's real .env.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.routers import auth as auth_router


class FakeEnvStore:
    def __init__(self, initial: dict):
        self.values = dict(initial)

    def reload(self):
        pass

    def get(self, key, default=""):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


def test_logout_clears_jwt_keeps_phone_and_device(monkeypatch):
    fake = FakeEnvStore({
        "YC_JWT": "some.jwt.token",
        "YC_PHONE_E164": "+37455285320",
        "YC_PHONE_LOCAL": "55285320",
        "YC_DEVICE_ID": "abc123",
    })
    monkeypatch.setattr(auth_router, "env_store", fake)

    client = TestClient(app)

    status_before = client.get("/api/auth/status").json()
    assert status_before["authenticated"] is True

    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.json() == {"authenticated": False}

    status_after = client.get("/api/auth/status").json()
    assert status_after["authenticated"] is False
    assert status_after["phone_e164"] == "+37455285320"  # phone preserved for a fast re-login

    assert fake.values["YC_JWT"] == ""
    assert fake.values["YC_DEVICE_ID"] == "abc123"  # untouched
