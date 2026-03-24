#!/usr/bin/env python3
"""
Interactive splitter for manual expenses (restaurants, cafes, etc.).

Produces the same split JSON format as split_basket.py so generate_csv.py
can consume it without changes.

Usage:
  python tools/manual_split.py
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from split_basket import (
    SEP, SEP_DBL,
    parse_assignment, resolve_name,
    collect_payment_info,
    compute_totals, allocate_fees,
    print_summary, _detect_method,
)

ROOT     = Path(__file__).parent.parent
ENV_PATH = ROOT / ".env"
TMP_DIR  = ROOT / ".tmp"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """Convert a session name to a safe filename stem."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text or "manual"


def _parse_service(raw: str, price: int) -> int:
    """Parse service charge: '10%' → 10% of price, '350' → 350 AMD, '' → 0."""
    raw = raw.strip()
    if not raw:
        return 0
    if raw.endswith("%"):
        pct = float(raw.rstrip("%"))
        return int(round(price * pct / 100))
    return int(round(float(raw)))


def _prompt(text: str) -> str:
    try:
        return input(text).strip()
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        sys.exit(0)


# ── Item entry loop ───────────────────────────────────────────────────────────

def collect_items(participants: list) -> list:
    items = []
    seq   = 0

    while True:
        seq += 1
        print(f"\n{SEP}")
        print(f"  Item {seq}")

        name = _prompt("  Name: ")
        if not name:
            name = f"Item {seq}"

        while True:
            try:
                price = int(round(float(_prompt("  Price (AMD): "))))
                if price >= 0:
                    break
            except ValueError:
                pass
            print("  [!] Enter a positive number.")

        svc_raw = _prompt("  Service charge (% or AMD, or Enter to skip): ")
        service = _parse_service(svc_raw, price)
        net     = price + service

        print(f"  Net: {net:,} AMD" + (f"  (price {price:,} + service {service:,})" if service else ""))
        print(f"{SEP}")
        print(f"  Participants: {', '.join(participants)}")
        print(f"  Formats: Enter=all equal | me,mahdi | me:60%,mahdi:40% | me:1200,mahdi:600")

        while True:
            try:
                raw     = _prompt("  Assign > ")
                result, weights = parse_assignment(raw, participants, net)
                parts_str = "  →  " + "  |  ".join(
                    f"{n}: {a:,} AMD" for n, a in result.items() if a > 0
                )
                print(parts_str)
                break
            except ValueError as e:
                print(f"  [!] {e}")

        method = _detect_method(raw, result)
        items.append({
            "name":               name,
            "price":              price,
            "service":            service,
            "net_price":          net,
            "assignments":        result,
            "assignment_weights": weights,
            "split_method":       method,
            "is_canceled":        False,
        })

        another = _prompt("\n  Add another item? ([Y]es / [N]o): ").lower()
        if another not in ("y", "yes", ""):
            break

    return items


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    load_dotenv(ENV_PATH)
    TMP_DIR.mkdir(exist_ok=True)

    # ── Participants ─────────────────────────────────────────────────────────
    defaults = [p.strip() for p in os.getenv("DEFAULT_PARTICIPANTS", "Me,Mahdi,Amir").split(",") if p.strip()]

    print(f"\n{SEP_DBL}")
    print(f"  MANUAL SPLIT")
    print(f"{SEP_DBL}")
    print(f"  Default participants: {', '.join(defaults)}")

    temp_raw     = _prompt("  Temporary participants? (comma-separated, or Enter to skip): ")
    temp_list    = [p.strip() for p in temp_raw.split(",") if p.strip()] if temp_raw else []
    participants = defaults + temp_list

    if temp_list:
        print(f"  Active participants: {', '.join(participants)}")

    # ── Session name ─────────────────────────────────────────────────────────
    session_name = _prompt("\n  Session name (e.g. Kavkaz restaurant): ") or "manual"
    slug         = _slugify(session_name)

    # ── Items ────────────────────────────────────────────────────────────────
    assigned_items = collect_items(participants)

    # ── Totals (no order-level fees for manual splits) ───────────────────────
    empty_order  = {"delivery_fee": 0, "service_fee": 0, "driver_tip": 0}
    item_totals  = {p: sum(it["assignments"].get(p, 0) for it in assigned_items) for p in participants}
    fee_allocs   = allocate_fees(participants, item_totals, empty_order)
    totals       = compute_totals(participants, assigned_items, fee_allocs)
    order_total  = sum(it["net_price"] for it in assigned_items)

    # Fake order dict for print_summary
    fake_order = {
        "order_id":    session_name,
        "total_to_pay": order_total,
        **empty_order,
    }
    print_summary(participants, totals, fake_order)

    # ── Payment method ───────────────────────────────────────────────────────
    currency = collect_payment_info(participants, totals)

    # ── Save split JSON ──────────────────────────────────────────────────────
    split_data = {
        "session_name": session_name,
        "order_id":     slug,
        "split_date":   datetime.now(tz=timezone.utc).isoformat(),
        "participants": participants,
        "items":        assigned_items,
        "fees":         empty_order,
        "fee_allocations": fee_allocs,
        "totals":       totals,
        "currency":     currency,
        "order_total":  order_total,
        "order_meta": {
            "create_date":    datetime.now(tz=timezone.utc).date().isoformat(),
            "status_label":   "Manual",
            "branch_address": session_name,
            "payment_label":  currency.get("method", "cash").capitalize(),
            "is_delivery":    False,
        },
    }

    split_path = TMP_DIR / f"split_{slug}.json"
    split_path.write_text(json.dumps(split_data, indent=2, ensure_ascii=False, default=str))
    print(f"\n  Saved: {split_path}")
    print(f"  Next : python tools/generate_csv.py {slug}")

    return slug


if __name__ == "__main__":
    main()
