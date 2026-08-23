"""Settings for the web backend. Reads the same root .env the CLI uses."""

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

from . import sys_path  # noqa: F401  (side effect: primes sys.path for tools/)

REPO_ROOT = sys_path.REPO_ROOT
ENV_PATH = REPO_ROOT / ".env"
TMP_DIR = REPO_ROOT / ".tmp"
FRONTEND_DIST = REPO_ROOT / "web" / "frontend" / "dist"
DB_PATH = TMP_DIR / "app.db"

TMP_DIR.mkdir(exist_ok=True)

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
