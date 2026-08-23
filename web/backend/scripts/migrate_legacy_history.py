"""One-time, manually-run migration: makes the pre-multi-tenancy split/order
files in data/ (created before per-account ownership existed) visible in the
web app's History for the legacy account (see migrate_legacy_env.py).

Per-account ownership is done by prefixing a filename with the owner's
numeric id (split_<user_id>_<id>.json — see persistence.scoped_id()). Files
from before that scheme existed have no such prefix at all
(split_<id>.json), so they don't match anyone's History query.

This script COPIES (never moves/renames) every unprefixed split_*.json and
order_*.json in data/ into a copy owned by LEGACY_USER_ID, leaving the
originals untouched — the CLI's tools (generate_csv.py, split_basket.py,
etc.) read those exact plain filenames directly and must keep working
unmodified. Report CSVs aren't copied: the web app regenerates them on
demand from the split JSON.

Run once, after migrate_legacy_env.py has created the legacy account:

    python web/backend/scripts/migrate_legacy_history.py

Idempotent: already-copied files are skipped, so re-running is harmless
(e.g. if new legacy-style files show up later from the CLI).
"""

import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # web/backend/

from app import sys_path as _sys_path  # noqa: E402,F401
from app.config import DATA_DIR  # noqa: E402
from app.models.user import LEGACY_USER_ID  # noqa: E402
from app.services.persistence import validate_id  # noqa: E402

# Matches an ALREADY-owned file (split_<digits>_<id>.json) so it's skipped —
# only bare, pre-multi-tenancy filenames get copied.
_OWNED_RE = re.compile(r"^(split|order)_\d+_.+$")


def _migrate(kind: str) -> int:
    copied = 0
    for path in sorted(DATA_DIR.glob(f"{kind}_*.json")):
        if _OWNED_RE.match(path.stem):
            continue  # already owned by some account — not a legacy file
        raw_id = path.stem.removeprefix(f"{kind}_")
        try:
            validate_id(raw_id)
        except Exception:
            print(f"Skipping {path.name} — id fails validation.")
            continue
        dest = DATA_DIR / f"{kind}_{LEGACY_USER_ID}_{raw_id}.json"
        if dest.exists():
            continue  # already migrated
        shutil.copy2(path, dest)
        print(f"Copied {path.name} -> {dest.name}")
        copied += 1
    return copied


def main() -> None:
    split_count = _migrate("split")
    order_count = _migrate("order")
    print(f"\nDone: {split_count} split file(s), {order_count} order cache(s) "
          f"now visible in History for the legacy account (id={LEGACY_USER_ID}).")
    print("Originals were left in place — the CLI's tools are unaffected.")


if __name__ == "__main__":
    main()
