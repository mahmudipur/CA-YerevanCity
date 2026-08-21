"""Web-friendly wrapper around auth_yc.py's 3-step OTP flow (unchanged yc_client calls)."""

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import sys_path  # noqa: F401
from ..services import env_store

from yc_client import YCError, confirm_code, send_code, verify  # noqa: E402

router = APIRouter(prefix="/api/auth", tags=["auth"])


class SendCodeBody(BaseModel):
    phone_local: str | None = None
    phone_e164: str | None = None


class VerifyBody(BaseModel):
    phone_e164: str | None = None
    code: str


@router.get("/status")
def status():
    env_store.reload()
    token = env_store.get("YC_JWT")
    phone_e164 = env_store.get("YC_PHONE_E164")
    phone_local = env_store.get("YC_PHONE_LOCAL")
    return {
        "authenticated": bool(token) and token != "nothing",
        "phone_e164": phone_e164 or None,
        "phone_local": phone_local or None,
    }


@router.post("/send-code")
def send_code_endpoint(body: SendCodeBody):
    phone_local = (body.phone_local or env_store.get("YC_PHONE_LOCAL")).strip()
    phone_e164 = (body.phone_e164 or env_store.get("YC_PHONE_E164")).strip()
    if not phone_local or not phone_e164:
        raise HTTPException(status_code=422, detail="Phone number is required.")

    device_id = env_store.get("YC_DEVICE_ID")
    if not device_id:
        device_id = uuid.uuid4().hex + "tAyn"  # matches auth_yc.py's format
        env_store.set("YC_DEVICE_ID", device_id)

    try:
        code = confirm_code()
        send_code(phone_local, device_id, code)
    except YCError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"sent": True, "phone_e164": phone_e164}


@router.post("/verify")
def verify_endpoint(body: VerifyBody):
    phone_e164 = (body.phone_e164 or env_store.get("YC_PHONE_E164")).strip()
    if not phone_e164:
        raise HTTPException(status_code=422, detail="Phone number is required.")
    if len(body.code) != 6 or not body.code.isdigit():
        raise HTTPException(status_code=422, detail="Invalid OTP format. Expected exactly 6 digits.")

    try:
        jwt = verify(phone_e164, body.code)
    except YCError as e:
        raise HTTPException(status_code=502, detail=f"Verification failed: {e}")

    env_store.set("YC_JWT", jwt)
    env_store.set("YC_PHONE_E164", phone_e164)
    return {"authenticated": True}


@router.post("/logout")
def logout():
    """
    Clears YC_JWT from .env (the same file/mechanism auth_yc.py writes to).
    Note this credential is shared with the terminal CLI by design (see
    workflows/web_app.md) — logging out here also logs the terminal out,
    and `python tools/auth_yc.py` will be needed there too until either
    side signs back in. Phone number and device id are left in place so
    a fresh sign-in doesn't need to re-enter them.
    """
    env_store.set("YC_JWT", "")
    return {"authenticated": False}
