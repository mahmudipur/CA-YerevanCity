"""Signed app-session cookie: round-trip, expiry, tamper-rejection."""

import pytest
from fastapi import HTTPException

from app.services import app_session


def test_round_trips_telegram_id():
    token = app_session.issue_session_token(42)
    assert app_session.verify_session_token(token) == 42


def test_tampered_token_is_rejected():
    token = app_session.issue_session_token(42)
    # Flip a character in the middle (not the last one — trailing base64
    # padding bits can be redundant and not actually change the decoded
    # bytes, making that particular flip a false negative for this test).
    mid = len(token) // 2
    flipped = "a" if token[mid] != "a" else "b"
    tampered = token[:mid] + flipped + token[mid + 1:]
    with pytest.raises(HTTPException) as exc:
        app_session.verify_session_token(tampered)
    assert exc.value.status_code == 401


def test_expired_token_is_rejected(monkeypatch):
    token = app_session.issue_session_token(42)
    # -1, not 0: itsdangerous only expires when elapsed > max_age, and a
    # same-second round-trip can have elapsed == 0.
    monkeypatch.setattr(app_session.settings, "app_session_max_age_seconds", -1)
    with pytest.raises(HTTPException) as exc:
        app_session.verify_session_token(token)
    assert exc.value.status_code == 401
