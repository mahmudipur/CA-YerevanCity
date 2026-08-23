"""Username/password login — the account-creation path that works with no
mail/SMS capability at all, since this app runs on a local machine behind a
free (rotating-URL) ngrok tunnel rather than a fixed domain Telegram's
widget could bind to.

Password reset has two tiers, both independent of email:
  1. Self-serve: a one-time recovery code shown once at signup (also
     re-generatable while logged in), consumed by /forgot-password.
  2. Admin fallback: scripts/reset_password.py, run locally by the app's
     operator, for when a user loses both their password and their code.
"""

import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, field_validator

from ..dependencies import get_current_user
from ..rate_limit import limiter
from ..services import app_session, user_store
from ..services.password_auth import PasswordTooLong, PasswordTooShort
from ..services.user_store import AuthedUser, UsernameTaken

router = APIRouter(prefix="/api/auth", tags=["password-auth"])

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,32}$")


def _validate_username(username: str) -> str:
    username = username.strip()
    if not _USERNAME_RE.match(username):
        raise HTTPException(
            status_code=422,
            detail="Username must be 3-32 characters: letters, numbers, '.', '_', or '-'.",
        )
    return username


class SignupBody(BaseModel):
    username: str
    password: str
    display_name: str | None = None
    email: str | None = None

    @field_validator("email")
    @classmethod
    def _bound_email(cls, v: str | None) -> str | None:
        return v.strip()[:256] if v else None


class LoginBody(BaseModel):
    username: str
    password: str


class ForgotPasswordBody(BaseModel):
    username: str
    recovery_code: str
    new_password: str


class SetPasswordBody(BaseModel):
    username: str
    password: str


@router.post("/signup")
@limiter.limit("5/hour")
def signup(request: Request, body: SignupBody, response: Response):
    username = _validate_username(body.username)
    try:
        user, recovery_code = user_store.create_password_account(
            username, body.password, display_name=body.display_name, email=body.email,
        )
    except UsernameTaken:
        raise HTTPException(status_code=409, detail="That username is already taken.")
    except (PasswordTooShort, PasswordTooLong) as e:
        raise HTTPException(status_code=422, detail=str(e))

    app_session.set_session_cookie(response, user.id)
    return {**user_store.to_public_profile(user), "recovery_code": recovery_code}


@router.post("/login")
@limiter.limit("10/hour")
def login(request: Request, body: LoginBody, response: Response):
    user = user_store.authenticate_password(body.username.strip(), body.password)
    if user is None:
        # Deliberately generic — never confirms whether the username exists.
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    app_session.set_session_cookie(response, user.id)
    return user_store.to_public_profile(user)


@router.post("/forgot-password")
@limiter.limit("5/hour")
def forgot_password(request: Request, body: ForgotPasswordBody, response: Response):
    try:
        result = user_store.reset_password_with_recovery_code(
            body.username.strip(), body.recovery_code, body.new_password,
        )
    except (PasswordTooShort, PasswordTooLong) as e:
        raise HTTPException(status_code=422, detail=str(e))
    if result is None:
        raise HTTPException(status_code=401, detail="Invalid username or recovery code.")

    user, new_recovery_code = result
    app_session.set_session_cookie(response, user.id)
    return {**user_store.to_public_profile(user), "recovery_code": new_recovery_code}


@router.post("/regenerate-recovery-code")
def regenerate_recovery_code(user: AuthedUser = Depends(get_current_user)):
    new_code = user_store.regenerate_recovery_code(user.id)
    return {"recovery_code": new_code}


@router.post("/set-password")
@limiter.limit("10/hour")
def set_password(request: Request, body: SetPasswordBody, user: AuthedUser = Depends(get_current_user)):
    """Adds username/password login to an already-authenticated (typically
    Telegram-first) account, so it stops depending on Telegram alone."""
    username = _validate_username(body.username)
    try:
        recovery_code = user_store.add_password_login(user.id, username, body.password)
    except UsernameTaken:
        raise HTTPException(status_code=409, detail="That username is already taken.")
    except (PasswordTooShort, PasswordTooLong) as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"recovery_code": recovery_code}
