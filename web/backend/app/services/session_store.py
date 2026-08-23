"""In-memory store of in-progress SplitSession objects, keyed by session_id
and scoped by telegram_id. Kept in-memory (not SQLite) deliberately — this
state is already best-effort/transient by design (an aborted session loses
progress, exactly like the CLI); only *finished* splits need durable,
per-user storage (see persistence.py).

Ownership is enforced here: get() 404s (not 403, to avoid confirming a
session_id exists at all) if the caller's telegram_id doesn't match the
session's owner. Note this only survives a single process/worker — if the
deployment ever needs multi-worker or restart-safe wizard state, move this
into SQLite with a TTL-cleanup job instead.
"""

import uuid

from fastapi import HTTPException

from ..models.session import SplitSession

_SESSIONS: dict[str, SplitSession] = {}


def create(telegram_id: int, **kwargs) -> SplitSession:
    session_id = uuid.uuid4().hex
    session = SplitSession(session_id=session_id, telegram_id=telegram_id, **kwargs)
    _SESSIONS[session_id] = session
    return session


def get(session_id: str, telegram_id: int) -> SplitSession:
    session = _SESSIONS.get(session_id)
    if session is None or session.telegram_id != telegram_id:
        raise HTTPException(status_code=404, detail="Session not found or expired.")
    return session


def delete(session_id: str, telegram_id: int) -> None:
    session = _SESSIONS.get(session_id)
    if session is not None and session.telegram_id == telegram_id:
        _SESSIONS.pop(session_id, None)
