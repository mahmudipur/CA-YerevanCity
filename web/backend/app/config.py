"""Settings for the web backend. Reads the same root .env the CLI uses."""

from pathlib import Path

from . import sys_path  # noqa: F401  (side effect: primes sys.path for tools/)

REPO_ROOT = sys_path.REPO_ROOT
ENV_PATH = REPO_ROOT / ".env"
TMP_DIR = REPO_ROOT / ".tmp"
FRONTEND_DIST = REPO_ROOT / "web" / "frontend" / "dist"

TMP_DIR.mkdir(exist_ok=True)
