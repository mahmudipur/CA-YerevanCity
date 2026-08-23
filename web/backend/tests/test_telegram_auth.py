"""HMAC verification for the classic Telegram Login Widget payload."""

import hashlib
import hmac
import time

import pytest
from fastapi import HTTPException

from app.config import settings
from app.services import telegram_auth

BOT_TOKEN = settings.telegram_bot_token  # fixed test value from conftest.py


def _signed_payload(**fields) -> dict:
    base = {
        "id": 12345,
        "first_name": "Ada",
        "username": "ada",
        "auth_date": int(time.time()),
    }
    base.update(fields)
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    data_check_string = "\n".join(f"{k}={base[k]}" for k in sorted(base))
    base["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return base


def test_valid_payload_is_accepted():
    payload = _signed_payload()
    result = telegram_auth.verify_telegram_login(payload)
    assert result["id"] == 12345


def test_tampered_field_is_rejected():
    payload = _signed_payload()
    payload["first_name"] = "Eve"  # tampered after the hash was computed
    with pytest.raises(HTTPException) as exc:
        telegram_auth.verify_telegram_login(payload)
    assert exc.value.status_code == 401


def test_wrong_hash_is_rejected():
    payload = _signed_payload()
    payload["hash"] = "0" * 64
    with pytest.raises(HTTPException) as exc:
        telegram_auth.verify_telegram_login(payload)
    assert exc.value.status_code == 401


def test_stale_auth_date_is_rejected():
    payload = _signed_payload(auth_date=int(time.time()) - settings.telegram_auth_max_age_seconds - 10)
    with pytest.raises(HTTPException) as exc:
        telegram_auth.verify_telegram_login(payload)
    assert exc.value.status_code == 401


def test_missing_required_field_is_rejected():
    payload = _signed_payload()
    del payload["hash"]
    with pytest.raises(HTTPException) as exc:
        telegram_auth.verify_telegram_login(payload)
    assert exc.value.status_code == 401
