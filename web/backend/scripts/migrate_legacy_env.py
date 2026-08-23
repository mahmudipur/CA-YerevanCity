"""One-time, manually-run migration: copies the current root .env's YC
credentials (the owner's own account, from before multi-tenancy existed)
into a reserved `LEGACY_USER_ID` row, and gives that row a real
username/password login so it's immediately usable — not an inert
placeholder — regardless of whether Telegram ever gets configured.

This is NOT auto-run on every boot — run it once, by hand, after deploying
the multi-tenant code:

    python web/backend/scripts/migrate_legacy_env.py --username you [--password ...]

Omit --password to be prompted (hidden input). Idempotent: running it again
updates the same row (and lets you change the password) rather than
creating a duplicate.

Pass --claim-legacy USER_ID to also copy the legacy YC secrets onto a
different account (e.g. one you later signed into via Telegram — its id is
in GET /api/auth/me's `id` field) if you'd rather use that account instead
of logging in as the legacy one directly.

SECURITY NOTE: the .env being migrated here was exposed over an
unauthenticated public ngrok tunnel during development. Treat its YC_JWT as
already compromised — after running this migration, sign back into YC
(POST /api/auth/send-code + /verify) to obtain a fresh JWT rather than
trusting the migrated one long-term.
"""

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # web/backend/

from app import sys_path as _sys_path  # noqa: E402,F401
from app.config import ENV_PATH  # noqa: E402
from app.db import init_db  # noqa: E402
from app.models.user import LEGACY_USER_ID  # noqa: E402
from app.services import user_store  # noqa: E402
from app.services.password_auth import PasswordTooLong, PasswordTooShort  # noqa: E402
from app.services.user_store import UsernameTaken  # noqa: E402
from dotenv import dotenv_values  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True, help="username for your immediately-usable login")
    parser.add_argument("--password", help="omit to be prompted (hidden input) instead")
    parser.add_argument(
        "--claim-legacy",
        type=int,
        metavar="USER_ID",
        help="also copy the legacy YC secrets onto this user id",
    )
    args = parser.parse_args()

    if not ENV_PATH.exists():
        print(f"No .env found at {ENV_PATH} — nothing to migrate.")
        return

    env = dotenv_values(str(ENV_PATH))
    jwt = (env.get("YC_JWT") or "").strip()
    if not jwt or jwt == "nothing":
        print("Root .env has no YC_JWT set — nothing to migrate.")
        return

    password = args.password or getpass.getpass("Choose a password for this account: ")

    init_db()

    try:
        recovery_code = user_store.create_legacy_account(LEGACY_USER_ID, args.username, password)
    except UsernameTaken as e:
        print(f"Error: {e}")
        return
    except (PasswordTooShort, PasswordTooLong) as e:
        print(f"Error: {e}")
        return

    user_store.set_yc_secrets(
        LEGACY_USER_ID,
        phone_local=(env.get("YC_PHONE_LOCAL") or "").strip(),
        phone_e164=(env.get("YC_PHONE_E164") or "").strip(),
        device_id=(env.get("YC_DEVICE_ID") or "").strip(),
        jwt=jwt,
    )
    print(f"Migrated .env's YC credentials into user id={LEGACY_USER_ID}, username='{args.username}'.")
    print(f"SAVE THIS RECOVERY CODE (shown once): {recovery_code}")

    if args.claim_legacy is not None:
        target = args.claim_legacy
        if user_store.get(target) is None:
            print(f"No user row for id={target} yet — log into the app first, then re-run with --claim-legacy.")
            return
        user_store.set_yc_secrets(
            target,
            phone_local=(env.get("YC_PHONE_LOCAL") or "").strip(),
            phone_e164=(env.get("YC_PHONE_E164") or "").strip(),
            device_id=(env.get("YC_DEVICE_ID") or "").strip(),
            jwt=jwt,
        )
        print(f"Also copied legacy YC credentials onto user id={target}.")

    print("Reminder: rotate these credentials with a fresh OTP login — the .env they came from was exposed over an unauthenticated ngrok tunnel during development.")


if __name__ == "__main__":
    main()
