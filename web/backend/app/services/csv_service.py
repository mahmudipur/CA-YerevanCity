"""Invokes generate_csv.py's unmodified main() for a given split id, exactly
the way tools/run.py already does (patching sys.argv before calling main()).
Returns the path to the written CSV.

generate_csv.py hardcodes `TMP_DIR / f"split_{order_id}.json"` — to reuse it
unmodified under multi-tenancy, we pass it the *composite* `<telegram_id>_<id>`
as its "order_id" argv, matching the composite filenames persistence.py now
writes. The downloaded filename shown to the user still uses their own
plain split_id (see routers/export.py).
"""

import sys

from fastapi import HTTPException

from .. import sys_path  # noqa: F401
from ..config import TMP_DIR
from .persistence import scoped_id

import generate_csv  # noqa: E402


def generate(telegram_id: int, split_id: str) -> str:
    composite = scoped_id(telegram_id, split_id)
    split_path = TMP_DIR / f"split_{composite}.json"
    if not split_path.exists():
        raise HTTPException(status_code=404, detail=f"Split not found for {split_id}.")

    prev_argv = sys.argv
    try:
        sys.argv = [prev_argv[0], composite]
        generate_csv.main()
    finally:
        sys.argv = prev_argv

    out_path = TMP_DIR / f"report_{composite}.csv"
    return str(out_path)
