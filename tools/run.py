#!/usr/bin/env python3
"""
Full pipeline: fetch → split → CSV report.

Usage:
  python tools/run.py            # fetch latest order (cached if already fetched today)
  python tools/run.py --refresh  # force re-fetch from API
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import fetch_order
import split_basket
import generate_csv


def main() -> None:
    refresh = "--refresh" in sys.argv

    # Step 1 — fetch latest order
    order_id = fetch_order.main(refresh=refresh)

    # Steps 2 & 3 — need order_id in sys.argv
    sys.argv = [sys.argv[0], order_id]

    # Step 2 — interactive split
    split_basket.main()

    # Step 3 — generate CSV
    generate_csv.main()


if __name__ == "__main__":
    main()
