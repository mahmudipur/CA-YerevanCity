"""Local, human-operated fallback for a user who has lost both their
password and their recovery code. Since this app has no email/SMS
capability, you run this yourself and relay the new password out-of-band
(Telegram DM, WhatsApp, in person, etc.).

    python web/backend/scripts/reset_password.py <username> [--password ...]

Omit --password to auto-generate a random one (printed once, not stored
anywhere else). Does not touch that account's recovery code — the user can
regenerate their own via POST /api/auth/regenerate-recovery-code once
they're logged back in with the password you give them.
"""

import argparse
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # web/backend/

from app import sys_path as _sys_path  # noqa: E402,F401
from app.db import init_db  # noqa: E402
from app.services import user_store  # noqa: E402
from app.services.password_auth import PasswordTooLong, PasswordTooShort  # noqa: E402
from app.services.user_store import InvalidCredentials  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    parser.add_argument("--password", help="omit to auto-generate a random one")
    args = parser.parse_args()

    init_db()

    new_password = args.password or secrets.token_urlsafe(12)
    try:
        user_store.admin_set_password(args.username, new_password)
    except InvalidCredentials as e:
        print(f"Error: {e}")
        return
    except (PasswordTooShort, PasswordTooLong) as e:
        print(f"Error: {e}")
        return

    print(f"Password for '{args.username}' reset to: {new_password}")
    print("Relay this to them yourself — it is not stored or logged anywhere else.")


if __name__ == "__main__":
    main()
