"""Per-account storage (SQLite). `id` (autoincrement) is the one stable
identity every other per-tenant store (session_store, persistence, order
caches) is scoped to — `telegram_id` and `username`/`password_hash` are
optional, independent, and linkable ways to authenticate into that same row.

Replaces env_store.py for everything web-app/per-user; env_store.py remains
only for the legacy CLI-shared .env.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from ..db import session_scope
from ..models.user import User
from . import crypto, password_auth


class UsernameTaken(ValueError):
    pass


class TelegramAlreadyLinked(ValueError):
    pass


class InvalidCredentials(ValueError):
    pass


@dataclass
class AuthedUser:
    """Plaintext view of a User row — decrypted/derived once per request,
    never round-tripped back through the DB layer's raw columns directly."""

    id: int
    telegram_id: int | None
    telegram_username: str | None
    username: str | None
    first_name: str
    last_name: str | None
    photo_url: str | None
    email: str | None
    default_participants: str
    google_sheet_id: str | None
    yc_phone_local: str
    yc_phone_e164: str
    yc_device_id: str
    yc_jwt: str
    has_password: bool
    has_recovery_code: bool

    @property
    def yc_linked(self) -> bool:
        return bool(self.yc_jwt) and self.yc_jwt != "nothing"


def to_public_profile(user: AuthedUser) -> dict:
    """The shape returned to the frontend by every auth endpoint
    (/me, Telegram callback/link, signup/login/forgot-password) — never
    includes password_hash/recovery_code_hash or YC secrets."""
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "telegram_username": user.telegram_username,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "photo_url": user.photo_url,
        "email": user.email,
        "has_password": user.has_password,
        "has_recovery_code": user.has_recovery_code,
        "telegram_linked": user.telegram_id is not None,
        "yc_linked": user.yc_linked,
    }


def _decrypt(value: bytes | None) -> str:
    if not value:
        return ""
    return crypto.decrypt(value)


def _to_authed_user(row: User) -> AuthedUser:
    return AuthedUser(
        id=row.id,
        telegram_id=row.telegram_id,
        telegram_username=row.telegram_username,
        username=row.username,
        first_name=row.first_name,
        last_name=row.last_name,
        photo_url=row.photo_url,
        email=row.email,
        default_participants=row.default_participants or "Me",
        google_sheet_id=row.google_sheet_id,
        yc_phone_local=_decrypt(row.yc_phone_local_enc),
        yc_phone_e164=_decrypt(row.yc_phone_e164_enc),
        yc_device_id=_decrypt(row.yc_device_id_enc),
        yc_jwt=_decrypt(row.yc_jwt_enc),
        has_password=bool(row.password_hash),
        has_recovery_code=bool(row.recovery_code_hash),
    )


def get(user_id: int) -> AuthedUser | None:
    with session_scope() as db:
        row = db.get(User, user_id)
        return _to_authed_user(row) if row else None


# ── Telegram identity ─────────────────────────────────────────────────────────

def get_by_telegram_id(telegram_id: int) -> AuthedUser | None:
    with session_scope() as db:
        row = db.query(User).filter_by(telegram_id=telegram_id).one_or_none()
        return _to_authed_user(row) if row else None


def get_or_create_telegram_user(
    telegram_id: int,
    *,
    username: str | None,
    first_name: str,
    last_name: str | None,
    photo_url: str | None,
) -> AuthedUser:
    """Fresh Telegram sign-in (no existing session) — looks up by
    telegram_id, creating a brand-new account if none exists. Not to be
    confused with link_telegram(), which attaches Telegram to an ALREADY
    authenticated (password-login) account."""
    with session_scope() as db:
        row = db.query(User).filter_by(telegram_id=telegram_id).one_or_none()
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


def link_telegram(user_id: int, telegram_id: int, *, username: str | None, first_name: str,
                   last_name: str | None, photo_url: str | None) -> AuthedUser:
    """Attach a Telegram identity to an already-authenticated account.
    Raises TelegramAlreadyLinked if that telegram_id belongs to someone
    else already."""
    with session_scope() as db:
        existing = db.query(User).filter_by(telegram_id=telegram_id).one_or_none()
        if existing is not None and existing.id != user_id:
            raise TelegramAlreadyLinked("That Telegram account is already linked to a different user.")
        row = db.get(User, user_id)
        if row is None:
            raise ValueError(f"No user row for id={user_id}")
        row.telegram_id = telegram_id
        row.telegram_username = username
        if photo_url:
            row.photo_url = photo_url
        db.commit()
        db.refresh(row)
        return _to_authed_user(row)


# ── Username/password identity ───────────────────────────────────────────────

def get_by_username(username: str) -> AuthedUser | None:
    with session_scope() as db:
        row = db.query(User).filter_by(username=username).one_or_none()
        return _to_authed_user(row) if row else None


def create_password_account(
    username: str, password: str, *, display_name: str | None = None, email: str | None = None,
) -> tuple[AuthedUser, str]:
    """Returns (user, plaintext_recovery_code) — the code is shown to the
    caller exactly once and never recoverable again after this call."""
    password_hash = password_auth.hash_password(password)
    recovery_code = password_auth.generate_recovery_code()
    recovery_hash = password_auth.hash_recovery_code(recovery_code)

    with session_scope() as db:
        if db.query(User).filter_by(username=username).one_or_none() is not None:
            raise UsernameTaken(f"Username '{username}' is already taken.")
        now = datetime.now(tz=timezone.utc)
        row = User(
            username=username,
            password_hash=password_hash,
            recovery_code_hash=recovery_hash,
            first_name=display_name or username,
            email=email,
            created_at=now,
            last_login_at=now,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _to_authed_user(row), recovery_code


def authenticate_password(username: str, password: str) -> AuthedUser | None:
    with session_scope() as db:
        row = db.query(User).filter_by(username=username).one_or_none()
        if row is None or not row.password_hash:
            return None
        if not password_auth.verify_password(password, row.password_hash):
            return None
        row.last_login_at = datetime.now(tz=timezone.utc)
        db.commit()
        db.refresh(row)
        return _to_authed_user(row)


def reset_password_with_recovery_code(
    username: str, recovery_code: str, new_password: str,
) -> tuple[AuthedUser, str] | None:
    """Returns (user, new_plaintext_recovery_code) on success, None if the
    username/recovery code pair doesn't check out. The old code is
    single-use — a fresh one is issued alongside the new password."""
    with session_scope() as db:
        row = db.query(User).filter_by(username=username).one_or_none()
        if row is None or not row.recovery_code_hash:
            return None
        if not password_auth.verify_recovery_code(recovery_code, row.recovery_code_hash):
            return None
        row.password_hash = password_auth.hash_password(new_password)
        new_code = password_auth.generate_recovery_code()
        row.recovery_code_hash = password_auth.hash_recovery_code(new_code)
        db.commit()
        db.refresh(row)
        return _to_authed_user(row), new_code


def regenerate_recovery_code(user_id: int) -> str:
    """Self-service replacement for an authenticated user who still has a
    session but lost their code."""
    new_code = password_auth.generate_recovery_code()
    with session_scope() as db:
        row = db.get(User, user_id)
        if row is None:
            raise ValueError(f"No user row for id={user_id}")
        row.recovery_code_hash = password_auth.hash_recovery_code(new_code)
        db.commit()
    return new_code


def add_password_login(user_id: int, username: str, password: str) -> str:
    """'Set a password' for an existing Telegram-first account. Returns the
    plaintext recovery code (generated fresh, shown once)."""
    password_hash = password_auth.hash_password(password)
    recovery_code = password_auth.generate_recovery_code()
    recovery_hash = password_auth.hash_recovery_code(recovery_code)
    with session_scope() as db:
        clash = db.query(User).filter_by(username=username).one_or_none()
        if clash is not None and clash.id != user_id:
            raise UsernameTaken(f"Username '{username}' is already taken.")
        row = db.get(User, user_id)
        if row is None:
            raise ValueError(f"No user row for id={user_id}")
        row.username = username
        row.password_hash = password_hash
        row.recovery_code_hash = recovery_hash
        db.commit()
    return recovery_code


def create_legacy_account(user_id: int, username: str, password: str) -> str:
    """Used only by scripts/migrate_legacy_env.py to seed the
    pre-multi-tenancy owner's account at a fixed id (models.user.
    LEGACY_USER_ID) with a real, immediately-usable password login instead
    of an inert placeholder. Returns the plaintext recovery code (shown
    once, same as any other signup)."""
    password_hash = password_auth.hash_password(password)
    recovery_code = password_auth.generate_recovery_code()
    recovery_hash = password_auth.hash_recovery_code(recovery_code)
    with session_scope() as db:
        clash = db.query(User).filter_by(username=username).one_or_none()
        if clash is not None and clash.id != user_id:
            raise UsernameTaken(f"Username '{username}' is already taken.")
        row = db.get(User, user_id)
        now = datetime.now(tz=timezone.utc)
        if row is None:
            row = User(
                id=user_id, username=username, password_hash=password_hash,
                recovery_code_hash=recovery_hash, first_name=username,
                created_at=now, last_login_at=now,
            )
            db.add(row)
        else:
            row.username = username
            row.password_hash = password_hash
            row.recovery_code_hash = recovery_hash
        db.commit()
    return recovery_code


def admin_set_password(username: str, new_password: str) -> None:
    """Used only by scripts/reset_password.py — a local, human-operated
    fallback when a user has lost both their password and recovery code."""
    password_hash = password_auth.hash_password(new_password)
    with session_scope() as db:
        row = db.query(User).filter_by(username=username).one_or_none()
        if row is None:
            raise InvalidCredentials(f"No account with username '{username}'.")
        row.password_hash = password_hash
        db.commit()


# ── YC secrets / shared profile fields (unaffected by login method) ─────────

def set_yc_secrets(
    user_id: int,
    *,
    phone_local: str | None = None,
    phone_e164: str | None = None,
    device_id: str | None = None,
    jwt: str | None = None,
) -> None:
    """Encrypts and writes only the fields explicitly provided (mirrors
    env_store.set()'s single-key-at-a-time usage in the old auth flow)."""
    with session_scope() as db:
        row = db.get(User, user_id)
        if row is None:
            raise ValueError(f"No user row for id={user_id}")
        if phone_local is not None:
            row.yc_phone_local_enc = crypto.encrypt(phone_local)
        if phone_e164 is not None:
            row.yc_phone_e164_enc = crypto.encrypt(phone_e164)
        if device_id is not None:
            row.yc_device_id_enc = crypto.encrypt(device_id)
        if jwt is not None:
            row.yc_jwt_enc = crypto.encrypt(jwt)
        db.commit()


def clear_yc_jwt(user_id: int) -> None:
    """Sign out of YC only — phone/device id are kept so a fresh sign-in
    doesn't need to re-enter them (mirrors the old auth.py logout)."""
    set_yc_secrets(user_id, jwt="")


def set_default_participants(user_id: int, raw: str) -> None:
    with session_scope() as db:
        row = db.get(User, user_id)
        if row is None:
            raise ValueError(f"No user row for id={user_id}")
        row.default_participants = raw
        db.commit()


def set_google_sheet_id(user_id: int, sheet_id: str) -> None:
    with session_scope() as db:
        row = db.get(User, user_id)
        if row is None:
            raise ValueError(f"No user row for id={user_id}")
        row.google_sheet_id = sheet_id
        db.commit()
