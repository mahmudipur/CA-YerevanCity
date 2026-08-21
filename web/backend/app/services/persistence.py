"""Reads/writes .tmp/order_*.json and .tmp/split_*.json — same file shape
and location the CLI already uses, so both paths stay interchangeable."""

import json
import re
from datetime import datetime, timezone

from fastapi import HTTPException

from ..config import TMP_DIR

# order_id/split_id ultimately become part of a filename (split_<id>.json,
# order_<id>.json, report_<id>.csv). They're either a YC order id (KM...),
# a slugify()'d manual session name (already word-chars/underscore/hyphen
# only), or user-supplied via a URL path param — validate that last case
# explicitly before ever building a path from it, now that this server may
# be reachable beyond localhost (e.g. via an ngrok tunnel).
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def validate_id(value: str) -> str:
    if not _SAFE_ID.match(value):
        raise HTTPException(status_code=400, detail="Invalid id.")
    return value


def save_split(split_id: str, split_data: dict) -> str:
    validate_id(split_id)
    out_path = TMP_DIR / f"split_{split_id}.json"
    out_path.write_text(json.dumps(split_data, indent=2, ensure_ascii=False, default=str))
    return str(out_path)


def load_split(split_id: str) -> dict:
    validate_id(split_id)
    path = TMP_DIR / f"split_{split_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Split not found for {split_id}.")
    return json.loads(path.read_text())


def list_splits() -> list[dict]:
    rows = []
    for path in sorted(TMP_DIR.glob("split_*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        rows.append({
            "id": data.get("order_id", path.stem.removeprefix("split_")),
            "split_date": data.get("split_date"),
            "participants": data.get("participants", []),
            "order_total": data.get("order_total"),
            "status_label": (data.get("order_meta") or {}).get("status_label"),
            "session_name": data.get("session_name"),
        })
    return rows


def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
