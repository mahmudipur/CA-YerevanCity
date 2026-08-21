"""In-memory store of in-progress SplitSession objects, keyed by session_id."""

import uuid

from fastapi import HTTPException

from ..models.session import SplitSession

_SESSIONS: dict[str, SplitSession] = {}


def create(**kwargs) -> SplitSession:
    session_id = uuid.uuid4().hex
    session = SplitSession(session_id=session_id, **kwargs)
    _SESSIONS[session_id] = session
    return session


def get(session_id: str) -> SplitSession:
    session = _SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return session


def delete(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)
