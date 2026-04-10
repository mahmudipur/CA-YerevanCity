#!/usr/bin/env python3
"""
Full split pipeline — choose between a Yerevan City order or a manual expense.

Usage:
  python tools/run.py            # interactive menu
  python tools/run.py --refresh  # YC order: force re-fetch from API
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import fetch_order
import split_basket
import manual_split
import generate_csv

SEP = "─" * 60


def _prompt(text: str) -> str:
    try:
        return input(text).strip()
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        sys.exit(0)


def run_yc(refresh: bool = False) -> None:
    target = _prompt("  Order ID (Enter for latest): ")
    order_id = fetch_order.main(refresh=refresh, target_order_id=target)
    sys.argv  = [sys.argv[0], order_id]
    split_basket.main()
    generate_csv.main()


def run_manual() -> None:
    slug     = manual_split.main()
    sys.argv = [sys.argv[0], slug]
    generate_csv.main()


def main() -> None:
    refresh = "--refresh" in sys.argv

    print(f"\n{SEP}")
    print("  What would you like to split?")
    print("  [1] Yerevan City order")
    print("  [2] Manual expense  (restaurant, cafe, etc.)")
    print(f"{SEP}")

    while True:
        choice = _prompt("  Choice: ")
        if choice in ("1", ""):
            run_yc(refresh=refresh)
            break
        if choice == "2":
            run_manual()
            break
        print("  [!] Enter 1 or 2.")


if __name__ == "__main__":
    main()
