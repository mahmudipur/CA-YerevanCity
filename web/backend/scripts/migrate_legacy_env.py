"""One-time, manually-run migration: copies the current root .env's YC
credentials (the owner's own account, from before multi-tenancy existed)
into a reserved `telegram_id=0` "legacy" row so the terminal CLI's shared
.env-based flow keeps working unmodified.

This is NOT auto-run on every boot — run it once, by hand, after deploying
the multi-tenant code:

    python web/backend/scripts/migrate_legacy_env.py [--claim-legacy TELEGRAM_ID]

Idempotent: running it again updates the same telegram_id=0 row rather than
creating a duplicate. Pass --claim-legacy to also copy the legacy YC secrets
onto a specific real Telegram account (use this once you've logged into the
app with your own Telegram account and know your telegram_id from
GET /api/auth/me) — useful so the owner doesn't have to re-run the YC OTP
flow a second time after switching to Telegram login.

SECURITY NOTE: the .env being migrated here was exposed over an
unauthenticated public ngrok tunnel during development. Treat its YC_JWT as
already compromised — after running this migration, sign back into YC
(POST /api/auth/send-code + /verify) to obtain a fresh JWT rather than
trusting the migrated one long-term.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # web/backend/

from app import sys_path as _sys_path  # noqa: E402,F401
from app.config import ENV_PATH  # noqa: E402
from app.db import init_db  # noqa: E402
from app.models.user import LEGACY_TELEGRAM_ID  # noqa: E402
from app.services import user_store  # noqa: E402
from dotenv import dotenv_values  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--claim-legacy",
        type=int,
        metavar="TELEGRAM_ID",
        help="also copy the legacy YC secrets onto this real telegram_id",
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

    init_db()

    if user_store.get(LEGACY_TELEGRAM_ID) is None:
        user_store.get_or_create(
            LEGACY_TELEGRAM_ID,
            username=None,
            first_name="Legacy (.env)",
            last_name=None,
            photo_url=None,
        )
    user_store.set_yc_secrets(
        LEGACY_TELEGRAM_ID,
        phone_local=(env.get("YC_PHONE_LOCAL") or "").strip(),
        phone_e164=(env.get("YC_PHONE_E164") or "").strip(),
        device_id=(env.get("YC_DEVICE_ID") or "").strip(),
        jwt=jwt,
    )
    print(f"Migrated .env's YC credentials into telegram_id={LEGACY_TELEGRAM_ID} (legacy row).")

    if args.claim_legacy is not None:
        target = args.claim_legacy
        if user_store.get(target) is None:
            print(f"No user row for telegram_id={target} yet — log into the app via Telegram first, then re-run.")
            return
        user_store.set_yc_secrets(
            target,
            phone_local=(env.get("YC_PHONE_LOCAL") or "").strip(),
            phone_e164=(env.get("YC_PHONE_E164") or "").strip(),
            device_id=(env.get("YC_DEVICE_ID") or "").strip(),
            jwt=jwt,
        )
        print(f"Also copied legacy YC credentials onto telegram_id={target}.")

    print("Reminder: rotate these credentials with a fresh OTP login — the .env they came from was exposed over an unauthenticated ngrok tunnel during development.")


if __name__ == "__main__":
    main()
