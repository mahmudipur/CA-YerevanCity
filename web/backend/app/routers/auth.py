"""Web-friendly wrapper around auth_yc.py's 3-step OTP flow (unchanged
yc_client calls). This is now "link my Yerevan City account" — a per-user
step gated behind having already logged into the app via Telegram
(routers/telegram_auth.py), not the app's login itself.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from .. import sys_path  # noqa: F401
from ..dependencies import get_current_user
from ..rate_limit import limiter
from ..services import user_store
from ..services.user_store import AuthedUser

from yc_client import YCError, confirm_code, send_code, verify  # noqa: E402

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SendCodeBody(BaseModel):
    phone_local: str | None = None
    phone_e164: str | None = None


class VerifyBody(BaseModel):
    phone_e164: str | None = None
    code: str


@router.get("/status")
def status(user: AuthedUser = Depends(get_current_user)):
    return {
        "authenticated": user.yc_linked,
        "phone_e164": user.yc_phone_e164 or None,
        "phone_local": user.yc_phone_local or None,
    }


@router.post("/send-code")
@limiter.limit("3/hour")
def send_code_endpoint(request: Request, body: SendCodeBody, user: AuthedUser = Depends(get_current_user)):
    phone_local = (body.phone_local or user.yc_phone_local).strip()
    phone_e164 = (body.phone_e164 or user.yc_phone_e164).strip()
    if not phone_local or not phone_e164:
        raise HTTPException(status_code=422, detail="Phone number is required.")

    device_id = user.yc_device_id
    if not device_id:
        device_id = uuid.uuid4().hex + "tAyn"  # matches auth_yc.py's format
        user_store.set_yc_secrets(user.telegram_id, device_id=device_id)

    try:
        code = confirm_code()
        send_code(phone_local, device_id, code)
    except YCError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"sent": True, "phone_e164": phone_e164}


@router.post("/verify")
@limiter.limit("5/10minute")
def verify_endpoint(request: Request, body: VerifyBody, user: AuthedUser = Depends(get_current_user)):
    phone_e164 = (body.phone_e164 or user.yc_phone_e164).strip()
    if not phone_e164:
        raise HTTPException(status_code=422, detail="Phone number is required.")
    if len(body.code) != 6 or not body.code.isdigit():
        raise HTTPException(status_code=422, detail="Invalid OTP format. Expected exactly 6 digits.")

    try:
        jwt = verify(phone_e164, body.code)
    except YCError as e:
        raise HTTPException(status_code=502, detail=f"Verification failed: {e}")

    user_store.set_yc_secrets(user.telegram_id, jwt=jwt, phone_e164=phone_e164)
    return {"authenticated": True}


@router.post("/logout")
def logout(user: AuthedUser = Depends(get_current_user)):
    """Clears this user's YC JWT only — their app (Telegram) session and
    phone/device id are left in place so a fresh sign-in doesn't need to
    re-enter them. Unrelated to /api/auth/telegram/logout, which signs out
    of the app entirely."""
    user_store.clear_yc_jwt(user.telegram_id)
    return {"authenticated": False}
