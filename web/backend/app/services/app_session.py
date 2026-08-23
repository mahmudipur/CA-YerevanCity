"""Signed, httpOnly app-session cookie identifying which telegram_id owns a
browser session. Separate from (a) the Telegram login step itself and (b)
the per-user Yerevan City JWT — this is purely "who is this browser."

Uses itsdangerous rather than a JWT library: this is a same-origin, opaque,
server-only-verified cookie (no third party ever needs to verify it), so a
signed token avoids JWT's `alg` footguns for no loss of functionality.
"""

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from fastapi import HTTPException, Response

from ..config import settings

COOKIE_NAME = "yc_session"
_SALT = "app-session"


class SessionNotConfigured(RuntimeError):
    pass


def _serializer() -> URLSafeTimedSerializer:
    secret = settings.app_session_secret.strip()
    if not secret:
        raise SessionNotConfigured(
            "APP_SESSION_SECRET is not set. Generate one with "
            "`python -c \"import secrets; print(secrets.token_urlsafe(32))\"` and add it to .env."
        )
    return URLSafeTimedSerializer(secret_key=secret, salt=_SALT)


def issue_session_token(telegram_id: int) -> str:
    return _serializer().dumps({"telegram_id": telegram_id})


def verify_session_token(token: str) -> int:
    try:
        data = _serializer().loads(token, max_age=settings.app_session_max_age_seconds)
    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session.")
    telegram_id = data.get("telegram_id")
    if not isinstance(telegram_id, int):
        raise HTTPException(status_code=401, detail="Invalid session.")
    return telegram_id


def set_session_cookie(response: Response, telegram_id: int) -> None:
    """Always issues a brand-new signed value — never reuses/upgrades a
    pre-existing cookie value, so login can't be used for session fixation."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=issue_session_token(telegram_id),
        max_age=settings.app_session_max_age_seconds,
        httponly=True,
        secure=settings.app_session_cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")
