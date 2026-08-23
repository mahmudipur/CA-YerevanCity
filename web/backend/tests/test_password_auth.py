"""Username/password signup, login, and recovery-code-based forgot-password."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _unique(name: str) -> str:
    import uuid
    return f"{name}_{uuid.uuid4().hex[:8]}"


def test_signup_returns_recovery_code_and_logs_in():
    username = _unique("alice")
    resp = client.post("/api/auth/signup", json={"username": username, "password": "correct horse battery"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["username"] == username
    assert body["has_password"] is True
    assert "recovery_code" in body and len(body["recovery_code"]) > 0
    assert "yc_session" in resp.cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == username


def test_signup_rejects_duplicate_username():
    username = _unique("bob")
    first = client.post("/api/auth/signup", json={"username": username, "password": "correct horse battery"})
    assert first.status_code == 200

    dup = client.post("/api/auth/signup", json={"username": username, "password": "another password"})
    assert dup.status_code == 409


def test_signup_rejects_short_password():
    resp = client.post("/api/auth/signup", json={"username": _unique("carol"), "password": "short"})
    assert resp.status_code == 422


def test_login_with_correct_credentials():
    username = _unique("dave")
    password = "a robust passphrase"
    client.post("/api/auth/signup", json={"username": username, "password": password})

    fresh_client = TestClient(app)  # no cookie carried over
    resp = fresh_client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    assert resp.json()["username"] == username


def test_login_rejects_wrong_password():
    username = _unique("erin")
    client.post("/api/auth/signup", json={"username": username, "password": "the real password"})

    fresh_client = TestClient(app)
    resp = fresh_client.post("/api/auth/login", json={"username": username, "password": "wrong password"})
    assert resp.status_code == 401


def test_login_rejects_unknown_username():
    fresh_client = TestClient(app)
    resp = fresh_client.post("/api/auth/login", json={"username": "no-such-user", "password": "whatever"})
    assert resp.status_code == 401


def test_forgot_password_with_valid_recovery_code():
    username = _unique("frank")
    signup = client.post("/api/auth/signup", json={"username": username, "password": "original password"})
    recovery_code = signup.json()["recovery_code"]

    fresh_client = TestClient(app)
    resp = fresh_client.post("/api/auth/forgot-password", json={
        "username": username, "recovery_code": recovery_code, "new_password": "brand new password",
    })
    assert resp.status_code == 200, resp.text
    new_code = resp.json()["recovery_code"]
    assert new_code != recovery_code  # old code is single-use, a fresh one is issued

    # New password works; old one doesn't.
    login_new = TestClient(app).post("/api/auth/login", json={"username": username, "password": "brand new password"})
    assert login_new.status_code == 200
    login_old = TestClient(app).post("/api/auth/login", json={"username": username, "password": "original password"})
    assert login_old.status_code == 401

    # Old recovery code no longer works (single-use).
    reuse = TestClient(app).post("/api/auth/forgot-password", json={
        "username": username, "recovery_code": recovery_code, "new_password": "yet another password",
    })
    assert reuse.status_code == 401


def test_forgot_password_rejects_wrong_recovery_code():
    username = _unique("grace")
    client.post("/api/auth/signup", json={"username": username, "password": "some password"})

    resp = TestClient(app).post("/api/auth/forgot-password", json={
        "username": username, "recovery_code": "WRONG-CODE-000", "new_password": "new password here",
    })
    assert resp.status_code == 401


def test_regenerate_recovery_code_requires_auth():
    resp = TestClient(app).post("/api/auth/regenerate-recovery-code")
    assert resp.status_code == 401


def test_regenerate_recovery_code_when_authenticated():
    username = _unique("heidi")
    signed_up = client.post("/api/auth/signup", json={"username": username, "password": "some password"})
    old_code = signed_up.json()["recovery_code"]

    resp = client.post("/api/auth/regenerate-recovery-code")
    assert resp.status_code == 200
    assert resp.json()["recovery_code"] != old_code
