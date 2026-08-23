"""Pure password/recovery-code hashing helpers — no DB access (see
user_store.py for that). Argon2id via argon2-cffi: no 72-byte silent-
truncation footgun like bcrypt, and it's the current OWASP-recommended
default for new applications.
"""

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash

# Hard cap, not just a UX nicety: Argon2 is deliberately slow, so accepting
# an arbitrarily long input turns every login attempt into a cheap DoS lever
# against your own CPU.
MAX_SECRET_LENGTH = 256
MIN_PASSWORD_LENGTH = 8

_hasher = PasswordHasher()


class PasswordTooLong(ValueError):
    pass


class PasswordTooShort(ValueError):
    pass


def _check_length(secret: str, *, minimum: int = 0) -> None:
    if len(secret) > MAX_SECRET_LENGTH:
        raise PasswordTooLong(f"Must be at most {MAX_SECRET_LENGTH} characters.")
    if minimum and len(secret) < minimum:
        raise PasswordTooShort(f"Must be at least {minimum} characters.")


def hash_password(password: str) -> str:
    _check_length(password, minimum=MIN_PASSWORD_LENGTH)
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash or len(password) > MAX_SECRET_LENGTH:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


def generate_recovery_code() -> str:
    """Human-typeable one-time recovery code, e.g. 'X7K9-QM3P-2NRT'."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I ambiguity
    groups = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
    return "-".join(groups)


def hash_recovery_code(code: str) -> str:
    _check_length(code)
    return _hasher.hash(code.strip().upper())


def verify_recovery_code(code: str, code_hash: str) -> bool:
    if not code_hash or len(code) > MAX_SECRET_LENGTH:
        return False
    try:
        return _hasher.verify(code_hash, code.strip().upper())
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False
