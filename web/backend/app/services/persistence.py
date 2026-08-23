"""Reads/writes data/order_*.json and data/split_*.json (persistent — not
.tmp/, see config.py). Per-user isolation
is done by prefixing the account's user_id onto the filename
(split_<uid>_<id>.json) rather than a per-user subdirectory — this keeps
the reused CLI scripts (generate_csv.py, which hardcodes
`TMP_DIR / f"split_{order_id}.json"`) working unmodified: callers just pass
the composite `"<uid>_<id>"` as the id those scripts expect. See
yc_adapter.py / csv_service.py for the same pattern applied to order caches
and CSV reports.
"""

import json
import re
from datetime import datetime, timezone

from fastapi import HTTPException

from ..config import TMP_DIR

# split_id/order_id ultimately become part of a filename. They're either a
# YC order id (KM...), a slugify()'d manual session name (already
# word-chars/underscore/hyphen only), or user-supplied via a URL path param
# — validate that last case explicitly before ever building a path from it,
# now that this server is reachable by any authenticated tenant, not just
# the one owner on localhost.
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def validate_id(value: str) -> str:
    if not _SAFE_ID.match(value):
        raise HTTPException(status_code=400, detail="Invalid id.")
    return value


def scoped_id(user_id: int, raw_id: str) -> str:
    """The composite id embedded in filenames — never returned to a client;
    routers/services only ever hand back the caller's own `raw_id`."""
    return f"{user_id}_{validate_id(raw_id)}"


def save_split(user_id: int, split_id: str, split_data: dict) -> str:
    out_path = TMP_DIR / f"split_{scoped_id(user_id, split_id)}.json"
    out_path.write_text(json.dumps(split_data, indent=2, ensure_ascii=False, default=str))
    return str(out_path)


def load_split(user_id: int, split_id: str) -> dict:
    path = TMP_DIR / f"split_{scoped_id(user_id, split_id)}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Split not found for {split_id}.")
    return json.loads(path.read_text())


def list_splits(user_id: int) -> list[dict]:
    prefix = f"split_{user_id}_"
    rows = []
    for path in sorted(TMP_DIR.glob(f"{prefix}*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        rows.append({
            "id": data.get("order_id", path.stem.removeprefix(prefix)),
            "split_date": data.get("split_date"),
            "participants": data.get("participants", []),
            "order_total": data.get("order_total"),
            "status_label": (data.get("order_meta") or {}).get("status_label"),
            "session_name": data.get("session_name"),
        })
    return rows


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
