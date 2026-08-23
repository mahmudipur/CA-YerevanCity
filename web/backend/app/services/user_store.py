"""Per-user account storage (SQLite). Replaces env_store.py for everything
web-app/per-user; env_store.py remains only for the legacy CLI-shared .env.

`get_or_create` is the single entry point that materializes a User row from
a verified Telegram login — an allowlist/invite gate, if ever added, is one
`if` at the top of this function.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from ..db import session_scope
from ..models.user import User
from . import crypto


@dataclass
class AuthedUser:
    """Plaintext view of a User row — decrypted once per request, never
    round-tripped back through the DB layer's encrypted columns directly."""

    telegram_id: int
    telegram_username: str | None
    first_name: str
    last_name: str | None
    photo_url: str | None
    default_participants: str
    google_sheet_id: str | None
    yc_phone_local: str
    yc_phone_e164: str
    yc_device_id: str
    yc_jwt: str

    @property
    def yc_linked(self) -> bool:
        return bool(self.yc_jwt) and self.yc_jwt != "nothing"


def _decrypt(value: bytes | None) -> str:
    if not value:
        return ""
    return crypto.decrypt(value)


def _to_authed_user(row: User) -> AuthedUser:
    return AuthedUser(
        telegram_id=row.telegram_id,
        telegram_username=row.telegram_username,
        first_name=row.first_name,
        last_name=row.last_name,
        photo_url=row.photo_url,
        default_participants=row.default_participants or "Me",
        google_sheet_id=row.google_sheet_id,
        yc_phone_local=_decrypt(row.yc_phone_local_enc),
        yc_phone_e164=_decrypt(row.yc_phone_e164_enc),
        yc_device_id=_decrypt(row.yc_device_id_enc),
        yc_jwt=_decrypt(row.yc_jwt_enc),
    )


def get(telegram_id: int) -> AuthedUser | None:
    with session_scope() as db:
        row = db.get(User, telegram_id)
        return _to_authed_user(row) if row else None


def get_or_create(
    telegram_id: int,
    *,
    username: str | None,
    first_name: str,
    last_name: str | None,
    photo_url: str | None,
) -> AuthedUser:
    with session_scope() as db:
        row = db.get(User, telegram_id)
        now = datetime.now(tz=timezone.utc)
        if row is None:
            row = User(
                telegram_id=telegram_id,
                telegram_username=username,
                first_name=first_name,
                last_name=last_name,
                photo_url=photo_url,
                created_at=now,
                last_login_at=now,
            )
            db.add(row)
        else:
            row.telegram_username = username
            row.first_name = first_name
            row.last_name = last_name
            row.photo_url = photo_url
            row.last_login_at = now
        db.commit()
        db.refresh(row)
        return _to_authed_user(row)


def set_yc_secrets(
    telegram_id: int,
    *,
    phone_local: str | None = None,
    phone_e164: str | None = None,
    device_id: str | None = None,
    jwt: str | None = None,
) -> None:
    """Encrypts and writes only the fields explicitly provided (mirrors
    env_store.set()'s single-key-at-a-time usage in the old auth flow)."""
    with session_scope() as db:
        row = db.get(User, telegram_id)
        if row is None:
            raise ValueError(f"No user row for telegram_id={telegram_id}")
        if phone_local is not None:
            row.yc_phone_local_enc = crypto.encrypt(phone_local)
        if phone_e164 is not None:
            row.yc_phone_e164_enc = crypto.encrypt(phone_e164)
        if device_id is not None:
            row.yc_device_id_enc = crypto.encrypt(device_id)
        if jwt is not None:
            row.yc_jwt_enc = crypto.encrypt(jwt)
        db.commit()


def clear_yc_jwt(telegram_id: int) -> None:
    """Sign out of YC only — phone/device id are kept so a fresh sign-in
    doesn't need to re-enter them (mirrors the old auth.py logout)."""
    set_yc_secrets(telegram_id, jwt="")


def set_default_participants(telegram_id: int, raw: str) -> None:
    with session_scope() as db:
        row = db.get(User, telegram_id)
        if row is None:
            raise ValueError(f"No user row for telegram_id={telegram_id}")
        row.default_participants = raw
        db.commit()


def set_google_sheet_id(telegram_id: int, sheet_id: str) -> None:
    with session_scope() as db:
        row = db.get(User, telegram_id)
        if row is None:
            raise ValueError(f"No user row for telegram_id={telegram_id}")
        row.google_sheet_id = sheet_id
        db.commit()
