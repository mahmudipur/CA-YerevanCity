"""Telegram Login Widget endpoints. Telegram is one of two independent ways
into an account (see routers/password_auth.py for the other) — the widget
either creates/logs into a Telegram-identified account (fresh sign-in), or
links Telegram onto an already-authenticated account (/link).

The existing /api/auth/* OTP flow (routers/auth.py) is a separate, later
step ("link my Yerevan City account") that requires being logged in here
(by either method) first.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, field_validator

from ..config import settings
from ..dependencies import get_current_user
from ..rate_limit import limiter
from ..services import app_session, telegram_auth, user_store
from ..services.user_store import AuthedUser, TelegramAlreadyLinked

router = APIRouter(prefix="/api/auth/telegram", tags=["telegram-auth"])

_MAX_STR = 256


class TelegramLoginBody(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str

    @field_validator("first_name", "last_name", "username")
    @classmethod
    def _bound_length(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return v[:_MAX_STR]

    @field_validator("photo_url")
    @classmethod
    def _https_only(cls, v: str | None) -> str | None:
        # Telegram-supplied strings are attacker-influenced (the user's own
        # Telegram profile fields) — never trust photo_url as a renderable
        # <img src> unless it's actually an https URL.
        if v and not v.lower().startswith("https://"):
            return None
        return v[:_MAX_STR] if v else v


@router.get("/config")
def telegram_config():
    """bot_username empty means Telegram login isn't configured — the
    frontend hides the widget entirely rather than showing a broken
    button/error in that case."""
    return {
        "bot_username": settings.telegram_bot_username,
        "domain": settings.telegram_login_domain,
    }


@router.post("/callback")
@limiter.limit("10/minute")
def telegram_callback(request: Request, body: TelegramLoginBody, response: Response):
    """Fresh Telegram sign-in — creates the account on first login, or logs
    into the existing one if this telegram_id has been seen before."""
    verified = telegram_auth.verify_telegram_login(body.model_dump())
    user = user_store.get_or_create_telegram_user(
        telegram_id=verified["id"],
        username=verified.get("username"),
        first_name=verified.get("first_name", ""),
        last_name=verified.get("last_name"),
        photo_url=verified.get("photo_url"),
    )
    app_session.set_session_cookie(response, user.id)
    return user_store.to_public_profile(user)


@router.post("/link")
@limiter.limit("10/minute")
def telegram_link(request: Request, body: TelegramLoginBody, user: AuthedUser = Depends(get_current_user)):
    """Attach Telegram to the CURRENTLY authenticated (e.g. password-login)
    account, instead of creating/logging into a separate one."""
    verified = telegram_auth.verify_telegram_login(body.model_dump())
    try:
        linked = user_store.link_telegram(
            user.id,
            verified["id"],
            username=verified.get("username"),
            first_name=verified.get("first_name", user.first_name),
            last_name=verified.get("last_name"),
            photo_url=verified.get("photo_url"),
        )
    except TelegramAlreadyLinked as e:
        raise HTTPException(status_code=409, detail=str(e))
    return user_store.to_public_profile(linked)


@router.post("/logout")
def telegram_logout(response: Response):
    """Signs out of the app entirely (clears the session cookie). Does not
    touch the linked YC account — see /api/auth/logout for that."""
    app_session.clear_session_cookie(response)
    return {"signed_out": True}


# Separate router (different prefix: /api/auth, not /api/auth/telegram) so
# GET /api/auth/me sits alongside every auth method's endpoints.
me_router = APIRouter(prefix="/api/auth", tags=["telegram-auth"])


@me_router.get("/me")
def me(user: AuthedUser = Depends(get_current_user)):
    return user_store.to_public_profile(user)
