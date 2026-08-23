"""Settings for the web backend. Reads the same root .env the CLI uses."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from . import sys_path  # noqa: F401  (side effect: primes sys.path for tools/)

REPO_ROOT = sys_path.REPO_ROOT
ENV_PATH = REPO_ROOT / ".env"
FRONTEND_DIST = REPO_ROOT / "web" / "frontend" / "dist"
# Every real record this app produces — accounts, and every split/order/
# report file (`persistence.py`, `yc_adapter.py`, `csv_service.py`) — lives
# here, not under `.tmp/`. `.tmp/` is documented (root CLAUDE.md) and
# treated as disposable/regenerable; nothing a user would consider "my
# data" may live somewhere that convention, or a stray `rm -rf .tmp`,
# could wipe. TMP_DIR is kept as an alias (rather than renaming every call
# site) precisely because there is no longer a meaningful distinction for
# this app: everything it writes is real data.
DATA_DIR = REPO_ROOT / "data"
TMP_DIR = DATA_DIR
# APP_DB_PATH override exists so the test suite (see tests/conftest.py) gets
# its own throwaway database instead of ever sharing — and potentially
# polluting or being polluted by — the real one.
DB_PATH = Path(os.environ["APP_DB_PATH"]) if os.environ.get("APP_DB_PATH") else DATA_DIR / "app.db"

DATA_DIR.mkdir(exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Loaded here (not just by env_store) so Settings below sees these vars
# regardless of import order.
load_dotenv(ENV_PATH)


class Settings(BaseSettings):
    """New app-level config (Telegram login, session/secret keys). Distinct
    from env_store.py, which is the *legacy* per-owner YC credential store
    shared with the terminal CLI — this class is for multi-tenant web-app
    config that never belonged in that shared file."""

    model_config = SettingsConfigDict(env_file=str(ENV_PATH), extra="ignore")

    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    # Domain BotFather's /setdomain is bound to. Must match exactly what the
    # widget is served from — read from env, never hardcoded, since the
    # production domain isn't finalized yet.
    telegram_login_domain: str = ""
    telegram_auth_max_age_seconds: int = 86400  # reject login payloads older than this

    app_master_key: str = ""       # Fernet key encrypting per-user YC secrets at rest
    app_session_secret: str = ""   # signs the app's own session cookie
    app_session_max_age_seconds: int = 60 * 60 * 24 * 30  # 30 days
    # Set to false only for local http:// dev without ngrok/TLS.
    app_session_cookie_secure: bool = True


settings = Settings()
