"""Verifies the classic Telegram Login Widget payload.

Algorithm (https://core.telegram.org/widgets/login-legacy):
    data_check_string = "\\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret_key = SHA256(bot_token)
    expected_hash = HMAC_SHA256(data_check_string, secret_key).hexdigest()
    valid iff expected_hash == data["hash"] (constant-time compare)

Also rejects payloads whose auth_date is stale, to bound replay of a leaked
callback payload.
"""

import hashlib
import hmac
import time

from fastapi import HTTPException

from ..config import settings

REQUIRED_FIELDS = ("id", "first_name", "auth_date", "hash")


def verify_telegram_login(data: dict) -> dict:
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] in (None, ""):
            raise HTTPException(status_code=401, detail=f"Telegram login payload missing '{field}'.")

    bot_token = settings.telegram_bot_token.strip()
    if not bot_token:
        raise HTTPException(status_code=500, detail="Telegram login is not configured on this server.")

    payload = {k: v for k, v in data.items() if k != "hash" and v is not None}
    data_check_string = "\n".join(f"{k}={payload[k]}" for k in sorted(payload))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, str(data["hash"])):
        raise HTTPException(status_code=401, detail="Telegram login verification failed.")

    try:
        auth_date = int(data["auth_date"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Telegram login payload has an invalid auth_date.")

    if time.time() - auth_date > settings.telegram_auth_max_age_seconds:
        raise HTTPException(status_code=401, detail="Telegram login has expired — please sign in again.")

    return data
