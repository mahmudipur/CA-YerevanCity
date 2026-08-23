"""Invokes generate_receipt_image.py's render_receipt_image() for a given
split id — same pattern as csv_service.py (reused, unmodified CLI tool
logic), just rendering a PNG instead of a CSV. See generate_receipt_image.py
for why this exists: the CSV has no on-screen equivalent, so this app's
users were screenshotting a spreadsheet as their Tricount receipt image,
which doesn't fit on a phone screen. This produces the finished image
directly — one file, no scrolling, works the same on any device.
"""

import json

from fastapi import HTTPException

from .. import sys_path  # noqa: F401
from ..config import TMP_DIR
from .persistence import scoped_id

from generate_receipt_image import render_receipt_image  # noqa: E402


def generate(user_id: int, split_id: str) -> str:
    composite = scoped_id(user_id, split_id)
    split_path = TMP_DIR / f"split_{composite}.json"
    if not split_path.exists():
        raise HTTPException(status_code=404, detail=f"Split not found for {split_id}.")

    split = json.loads(split_path.read_text())
    out_path = TMP_DIR / f"receipt_{composite}.png"
    render_receipt_image(split, out_path)
    return str(out_path)
