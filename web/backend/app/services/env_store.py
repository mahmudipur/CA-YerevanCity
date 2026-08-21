"""
Reads/writes the same root .env the terminal CLI (auth_yc.py) uses, via the
same python-dotenv set_key mechanism, so credentials are shared between the
terminal and web app on the same machine.
"""

import os

from dotenv import load_dotenv, set_key

from ..config import ENV_PATH

load_dotenv(ENV_PATH)


def get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def set(key: str, value: str) -> None:
    os.environ[key] = value
    set_key(str(ENV_PATH), key, value)


def reload() -> None:
    load_dotenv(ENV_PATH, override=True)
