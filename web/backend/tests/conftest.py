import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parents[1]
TOOLS_DIR = REPO_ROOT / "tools"

for p in (str(BACKEND_DIR), str(TOOLS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Fixed test-only secrets, set before any `app.*` module is imported (so
# pydantic-settings picks them up) — a real .env's APP_MASTER_KEY must never
# be used for tests, and re-running the suite with a random key each time
# would fail to decrypt whatever a previous run already wrote to the shared
# on-disk .tmp/app.db test DB.
os.environ.setdefault("APP_MASTER_KEY", "jDA2XvP4lvsyDIDqUWpJRq2olh5bH4CBilRvYeEMk0I=")
os.environ.setdefault("APP_SESSION_SECRET", "test-only-session-secret-do-not-use-in-prod")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TEST-BOT-TOKEN-not-real")
os.environ.setdefault("TELEGRAM_BOT_USERNAME", "test_bot")
os.environ.setdefault("TELEGRAM_LOGIN_DOMAIN", "localhost")
# TestClient talks to "http://testserver" (plain HTTP) — a real Secure
# cookie would be silently dropped by the client's cookie jar, which would
# make every cookie-based test fail for a reason that has nothing to do
# with the code under test.
os.environ.setdefault("APP_SESSION_COOKIE_SECURE", "false")

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "order_FIXTURE.json"


def load_fixture_order() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


# ── Auth fixtures ─────────────────────────────────────────────────────────────
# Every router now requires Depends(get_current_user)/require_yc_linked. Tests
# bypass real Telegram/OTP login via FastAPI's dependency_overrides, exactly
# the pattern the plan called for — most test bodies are otherwise unchanged.

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import init_db  # noqa: E402
from app.dependencies import get_current_user, require_yc_linked  # noqa: E402
from app.main import app  # noqa: E402
from app.services import user_store  # noqa: E402

TEST_TELEGRAM_ID = 999001

_DEFAULTS = dict(
    username="test_user",
    first_name="Test",
    last_name=None,
    photo_url=None,
    default_participants="Me",
    yc_phone_local="55000000",
    yc_phone_e164="+37455000000",
    yc_device_id="test-device",
    yc_jwt="test-jwt",
)


@pytest.fixture
def authed_user_factory():
    """Creates/resets a real row for TEST_TELEGRAM_ID in the (real, on-disk
    test) SQLite store and overrides get_current_user/require_yc_linked to
    re-fetch it fresh on every dependency resolution — so route handlers
    that mutate the row (e.g. logout) are reflected on the next request,
    exactly like production. Call with kwargs to customize, e.g.
    `authed_user_factory(default_participants="Alice,Bob")`."""

    def _make(**overrides):
        cfg = {**_DEFAULTS, **overrides}
        init_db()
        user_store.get_or_create(
            TEST_TELEGRAM_ID,
            username=cfg["username"],
            first_name=cfg["first_name"],
            last_name=cfg["last_name"],
            photo_url=cfg["photo_url"],
        )
        user_store.set_default_participants(TEST_TELEGRAM_ID, cfg["default_participants"])
        user_store.set_yc_secrets(
            TEST_TELEGRAM_ID,
            phone_local=cfg["yc_phone_local"],
            phone_e164=cfg["yc_phone_e164"],
            device_id=cfg["yc_device_id"],
            jwt=cfg["yc_jwt"],
        )
        fetch = lambda: user_store.get(TEST_TELEGRAM_ID)  # noqa: E731 - re-reads DB, not a frozen snapshot
        app.dependency_overrides[get_current_user] = fetch
        app.dependency_overrides[require_yc_linked] = fetch
        return fetch()

    yield _make
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_yc_linked, None)


@pytest.fixture
def authed_client(authed_user_factory):
    authed_user_factory()
    return TestClient(app)
