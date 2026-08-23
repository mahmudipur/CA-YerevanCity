"""FastAPI Depends() guards. Add `Depends(get_current_user)` (or
`Depends(require_yc_linked)`) to every route that touches per-user data —
today that's every router except telegram_auth's login endpoints and
/api/health."""

from fastapi import Cookie, Depends, HTTPException

from .services import app_session, user_store
from .services.user_store import AuthedUser


def get_current_user(yc_session: str | None = Cookie(default=None)) -> AuthedUser:
    if not yc_session:
        raise HTTPException(status_code=401, detail="Not signed in.")
    user_id = app_session.verify_session_token(yc_session)
    user = user_store.get(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Account not found. Please sign in again.")
    return user


def require_yc_linked(user: AuthedUser = Depends(get_current_user)) -> AuthedUser:
    if not user.yc_linked:
        raise HTTPException(status_code=401, detail="Not signed in. Complete the Yerevan City login first.")
    return user
