"""One tenant must never be able to read/mutate another tenant's split
session or saved split via a guessed/known id — the core IDOR risk this
multi-tenancy retrofit exists to close."""

import json

from app.config import TMP_DIR
from app.dependencies import get_current_user, require_yc_linked
from app.main import app
from app.services import persistence, session_store

USER_A = 700001
USER_B = 700002


def test_session_store_isolates_owners():
    session = session_store.create(USER_A, kind="manual", session_name="a-only", items=[])
    assert session_store.get(session.session_id, USER_A) is session

    try:
        session_store.get(session.session_id, USER_B)
        assert False, "expected 404 for a different owner"
    except Exception as e:
        assert getattr(e, "status_code", None) == 404


def test_persistence_isolates_owners(tmp_path, monkeypatch):
    split_data = {"order_id": "shared-name", "participants": ["Alice"]}
    persistence.save_split(USER_A, "shared-name", split_data)
    try:
        assert persistence.load_split(USER_A, "shared-name") == split_data
        try:
            persistence.load_split(USER_B, "shared-name")
            assert False, "expected 404 — B never saved a split with this id"
        except Exception as e:
            assert getattr(e, "status_code", None) == 404

        # Same raw id, different owners -> genuinely different files, not a collision.
        persistence.save_split(USER_B, "shared-name", {"order_id": "shared-name", "participants": ["Bob"]})
        assert persistence.load_split(USER_A, "shared-name")["participants"] == ["Alice"]
        assert persistence.load_split(USER_B, "shared-name")["participants"] == ["Bob"]

        a_ids = [row["id"] for row in persistence.list_splits(USER_A)]
        b_ids = [row["id"] for row in persistence.list_splits(USER_B)]
        assert "shared-name" in a_ids and "shared-name" in b_ids
        # list_splits(A) must not include B's file just because the raw id matches.
        assert len(persistence.list_splits(USER_A)) == 1
    finally:
        (TMP_DIR / f"split_{USER_A}_shared-name.json").unlink(missing_ok=True)
        (TMP_DIR / f"split_{USER_B}_shared-name.json").unlink(missing_ok=True)


def test_cross_tenant_session_access_returns_404_over_http():
    """Full HTTP-layer check: user A creates a session, user B (a different
    authenticated telegram_id) must get 404 trying to fetch it by id."""
    from app.services.user_store import AuthedUser

    def fake_user(tid):
        return AuthedUser(
            telegram_id=tid, telegram_username=None, first_name="T", last_name=None,
            photo_url=None, default_participants="Me", google_sheet_id=None,
            yc_phone_local="", yc_phone_e164="", yc_device_id="", yc_jwt="",
        )

    from fastapi.testclient import TestClient
    client = TestClient(app)

    app.dependency_overrides[get_current_user] = lambda: fake_user(USER_A)
    app.dependency_overrides[require_yc_linked] = lambda: fake_user(USER_A)
    created = client.post("/api/sessions", json={"kind": "manual", "session_name": "a-session"}).json()
    session_id = created["session_id"]

    app.dependency_overrides[get_current_user] = lambda: fake_user(USER_B)
    app.dependency_overrides[require_yc_linked] = lambda: fake_user(USER_B)
    try:
        resp = client.get(f"/api/sessions/{session_id}")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(require_yc_linked, None)
