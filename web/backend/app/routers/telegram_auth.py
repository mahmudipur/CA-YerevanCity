"""Telegram Login Widget endpoints — this is the app's actual login. The
existing /api/auth/* OTP flow (routers/auth.py) is a *second*, per-user step
("link my Yerevan City account") that requires being logged in here first.
"""

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, field_validator

from ..config import settings
from ..dependencies import get_current_user
from ..rate_limit import limiter
from ..services import app_session, telegram_auth, user_store
from ..services.user_store import AuthedUser

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


def _public_profile(user: AuthedUser) -> dict:
    return {
        "telegram_id": user.telegram_id,
        "username": user.telegram_username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "photo_url": user.photo_url,
        "yc_linked": user.yc_linked,
    }


@router.get("/config")
def telegram_config():
    return {
        "bot_username": settings.telegram_bot_username,
        "domain": settings.telegram_login_domain,
    }


@router.post("/callback")
@limiter.limit("10/minute")
def telegram_callback(request: Request, body: TelegramLoginBody, response: Response):
    verified = telegram_auth.verify_telegram_login(body.model_dump())
    user = user_store.get_or_create(
        telegram_id=verified["id"],
        username=verified.get("username"),
        first_name=verified.get("first_name", ""),
        last_name=verified.get("last_name"),
        photo_url=verified.get("photo_url"),
    )
    app_session.set_session_cookie(response, user.telegram_id)
    return _public_profile(user)


@router.post("/logout")
def telegram_logout(response: Response):
    """Signs out of the app entirely (clears the session cookie). Does not
    touch the linked YC account — see /api/auth/logout for that."""
    app_session.clear_session_cookie(response)
    return {"signed_out": True}


# Separate router (different prefix: /api/auth, not /api/auth/telegram) so
# GET /api/auth/me sits alongside the OTP-flow endpoints in routers/auth.py.
me_router = APIRouter(prefix="/api/auth", tags=["telegram-auth"])


@me_router.get("/me")
def me(user: AuthedUser = Depends(get_current_user)):
    return _public_profile(user)
