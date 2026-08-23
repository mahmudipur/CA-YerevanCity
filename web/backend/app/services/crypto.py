"""Fernet symmetric encryption for YC secrets at rest (phone/device-id/JWT).

Key comes from APP_MASTER_KEY (env var, never committed). Generate one with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Validated lazily (on first use, not at import time) so this module can be
imported freely — e.g. by tests that don't touch any Telegram/YC-linking
code path — without requiring the key to be configured.
"""

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings


class CryptoNotConfigured(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = settings.app_master_key.strip()
    if not key:
        raise CryptoNotConfigured(
            "APP_MASTER_KEY is not set. Generate one with "
            "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"` "
            "and add it to .env."
        )
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as e:
        raise CryptoNotConfigured(f"APP_MASTER_KEY is not a valid Fernet key: {e}") from e


def encrypt(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode())


def decrypt(ciphertext: bytes) -> str:
    try:
        return _fernet().decrypt(ciphertext).decode()
    except InvalidToken as e:
        raise CryptoNotConfigured("Stored secret could not be decrypted with the current APP_MASTER_KEY.") from e
