"""The `users` table: one row per Telegram account. YC secrets are stored
encrypted at rest (see services/crypto.py) — callers should go through
services/user_store.py rather than touching this model's *_enc columns
directly, so plaintext never leaks outside that one module."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base

# Reserved telegram_id for the pre-existing owner's account, migrated from
# the root .env by scripts/migrate_legacy_env.py. No real Telegram user has
# id 0, so this row is unreachable via Telegram login — it exists purely to
# keep the terminal CLI's shared .env flow working. See that script's
# docstring for the full rationale.
LEGACY_TELEGRAM_ID = 0


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    yc_phone_local_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    yc_phone_e164_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    yc_device_id_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    yc_jwt_enc: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    default_participants: Mapped[str] = mapped_column(String(512), nullable=False, default="Me")
    google_sheet_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
