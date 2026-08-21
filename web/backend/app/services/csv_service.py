"""
Invokes generate_csv.py's unmodified main() for a given split id, exactly the
way tools/run.py already does (patching sys.argv before calling main()).
Returns the path to the written CSV.
"""

import sys

from fastapi import HTTPException

from .. import sys_path  # noqa: F401
from ..config import TMP_DIR
from .persistence import validate_id

import generate_csv  # noqa: E402


def generate(split_id: str) -> str:
    validate_id(split_id)
    split_path = TMP_DIR / f"split_{split_id}.json"
    if not split_path.exists():
        raise HTTPException(status_code=404, detail=f"Split not found for {split_id}.")

    prev_argv = sys.argv
    try:
        sys.argv = [prev_argv[0], split_id]
        generate_csv.main()
    finally:
        sys.argv = prev_argv

    out_path = TMP_DIR / f"report_{split_id}.csv"
    return str(out_path)
