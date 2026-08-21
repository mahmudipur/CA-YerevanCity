"""
Import this module (for its side effect) before importing anything from the
project's tools/ package. It primes sys.path exactly the way every tools/*.py
script primes it for its own sibling imports, so split_math, split_basket,
fetch_order, manual_split, generate_csv, yc_client, interactive can be
imported unmodified from the web backend.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))
