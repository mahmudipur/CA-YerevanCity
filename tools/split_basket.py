#!/usr/bin/env python3
"""
Interactive per-item basket splitter.

Loads .tmp/order_{id}.json, walks through each active item and asks how to
split it, then computes per-person totals (including proportional fee
allocation) and writes .tmp/split_{id}.json.

Usage:
  python tools/split_basket.py <order_id>
  python tools/split_basket.py KM0029977560

Assignment input formats (case-insensitive names):
  <Enter> or all          → equal split among ALL active participants
  me                      → 100% to Me
  me,mahdi                → equal split between Me and Mahdi
  me:60%,mahdi:40%        → percentage (must sum to 100)
  me:1200,mahdi:600       → fixed AMD (must sum to item net price)
"""

import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from functools import reduce
from math import gcd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv

ROOT     = Path(__file__).parent.parent
ENV_PATH = ROOT / ".env"
TMP_DIR  = ROOT / ".tmp"

SEP     = "─" * 60
SEP_DBL = "═" * 60


# ── Maths ─────────────────────────────────────────────────────────────────────

def _largest_remainder(total: int, weights: dict) -> dict:
    """
    Split `total` (integer AMD) among keys proportionally to their weights.
    Uses the largest-remainder method so sum(result) == total always.
    weights: {key: numeric_weight}
    """
    weight_sum = sum(weights.values())
    if weight_sum == 0:
        return {k: 0 for k in weights}
    raw = {k: Decimal(total) * Decimal(str(v)) / Decimal(str(weight_sum))
           for k, v in weights.items()}
    floored = {k: int(v) for k, v in raw.items()}
    remainder = total - sum(floored.values())
    for k, _ in sorted(raw.items(), key=lambda x: -(x[1] % 1)):
        if remainder <= 0:
            break
        floored[k] += 1
        remainder -= 1
    assert sum(floored.values()) == total, "Rounding error"
    return floored


def _equal_split(names: list, total: int) -> dict:
    equal_weights = {n: 1 for n in names}
    return _largest_remainder(total, equal_weights)


def _pct_split(pct_dict: dict, total: int) -> dict:
    """pct_dict: {name: float_pct}. Must sum to 100."""
    return _largest_remainder(total, pct_dict)


# ── Name resolution ───────────────────────────────────────────────────────────

def resolve_name(raw: str, participants: list) -> str:
    """Case-insensitive, supports partial prefix. Raises ValueError if ambiguous/missing."""
    raw_lower = raw.strip().lower()
    exact = [p for p in participants if p.lower() == raw_lower]
    if len(exact) == 1:
        return exact[0]
    partial = [p for p in participants if p.lower().startswith(raw_lower)]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        raise ValueError(f"'{raw}' is ambiguous — matches: {partial}")
    raise ValueError(f"Unknown participant '{raw}'. Active: {participants}")


# ── Assignment parser ─────────────────────────────────────────────────────────

def parse_assignment(text: str, participants: list, net_price: int) -> tuple:
    """
    Parse the user's assignment string.
    Returns (int_amounts, display_weights):
      - int_amounts:      {participant: int} summing exactly to net_price (fee allocation)
      - display_weights:  {participant: number} the natural weights to show in the CSV,
                          exactly as entered:
                            equal / named subset → 1 per sharing person, 0 otherwise
                            percentage           → the pct value (e.g. 60, 40, 0)
                            fixed AMD            → GCD-reduced integers (e.g. 2, 1, 0)
    """
    text = text.strip()

    def _equal_weights(names):
        return {p: (1 if p in names else 0) for p in participants}

    # Default: equal split all
    if not text or text.lower() in ("all", "a"):
        return _equal_split(participants, net_price), _equal_weights(participants)

    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        return _equal_split(participants, net_price), _equal_weights(participants)

    has_colon = any(":" in p for p in parts)

    if not has_colon:
        # "me,mahdi" — equal among named
        names = [resolve_name(p, participants) for p in parts]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate participant in assignment.")
        return _equal_split(names, net_price), _equal_weights(names)

    # Has colons — percentage or fixed
    pairs = {}
    for part in parts:
        if ":" not in part:
            raise ValueError(f"Mixed format: '{part}' has no colon but others do.")
        name_raw, val_raw = part.split(":", 1)
        name = resolve_name(name_raw.strip(), participants)
        val_str = val_raw.strip()
        is_pct = val_str.endswith("%")
        pairs[name] = (float(val_str.rstrip("%")), is_pct)

    if len(pairs) != len(set(pairs.keys())):
        raise ValueError("Duplicate participant in assignment.")

    all_pct = all(is_pct for _, is_pct in pairs.values())
    all_amd = all(not is_pct for _, is_pct in pairs.values())

    if not all_pct and not all_amd:
        raise ValueError("Mix of % and AMD amounts not allowed. Use all % or all AMD.")

    if all_pct:
        pct_sum = sum(v for v, _ in pairs.values())
        if abs(pct_sum - 100) > 0.01:
            raise ValueError(f"Percentages sum to {pct_sum:.1f}%, must be 100%.")
        pct_map = {n: v for n, (v, _) in pairs.items()}
        weights = {p: round(pct_map.get(p, 0.0), 2) for p in participants}
        return _pct_split(pct_map, net_price), weights

    # Fixed AMD — reduce to smallest integer weights via GCD
    amounts = {n: int(round(v)) for n, (v, _) in pairs.items()}
    total_given = sum(amounts.values())
    if total_given != net_price:
        raise ValueError(
            f"Fixed amounts sum to {total_given:,} AMD, but item net price is {net_price:,} AMD."
        )
    nonzero_vals = [v for v in amounts.values() if v > 0]
    g = reduce(gcd, nonzero_vals) if nonzero_vals else 1
    weights = {p: amounts.get(p, 0) // g for p in participants}
    return amounts, weights


# ── Interactive assignment loop ───────────────────────────────────────────────

def assign_items(items: list, participants: list) -> list:
    """Walk through each active item and collect assignments. Returns enriched item list."""
    active = [(i, it) for i, it in enumerate(items) if not it["is_canceled"]]
    total_active = len(active)
    assigned = []

    for seq, (orig_idx, item) in enumerate(active, start=1):
        net = item["net_price"]
        qty = item["quantity"]
        unit = item.get("unit") or "pcs"
        qty_str = f"x{qty:.0f}" if qty == int(qty) else f"x{qty}"

        print(f"\n{SEP}")
        print(f"  Item {seq}/{total_active}")
        print(f"  {item['name']}")
        qty_line = f"  {qty_str} {unit}"
        if item["unit_price"]:
            qty_line += f"  ·  {item['unit_price']:,} AMD/unit"
        if item["discount"]:
            qty_line += f"  ·  Discount: -{item['discount']:,}"
        print(qty_line)
        print(f"  Net: {net:,} AMD")
        print(f"{SEP}")
        print(f"  Participants: {', '.join(participants)}")
        print(f"  Formats: Enter=all equal | me,mahdi | me:60%,mahdi:40% | me:1200,mahdi:600")

        while True:
            try:
                raw = input("  Assign > ").strip()
                result, weights = parse_assignment(raw, participants, net)
                # Show computed split for confirmation
                parts_str = "  →  " + "  |  ".join(
                    f"{n}: {a:,} AMD" for n, a in result.items() if a > 0
                )
                print(parts_str)
                break
            except ValueError as e:
                print(f"  [!] {e}")
            except (KeyboardInterrupt, EOFError):
                print("\nAborted.")
                sys.exit(0)

        # Determine method label for report
        method = _detect_method(raw.strip(), result)
        assigned.append({**item, "assignments": result, "assignment_weights": weights, "split_method": method})

    return assigned


def _detect_method(raw: str, result: dict) -> str:
    if not raw or raw.lower() in ("all", "a", ""):
        return "equal/all"
    if "%" in raw:
        return "percentage"
    if ":" in raw:
        return "fixed"
    if len(result) < 3 and "," in raw:
        return "equal/partial"
    if len(result) == 1:
        return "single"
    return "equal/partial"


# ── Fee allocation ────────────────────────────────────────────────────────────

def allocate_fees(participants: list, item_totals: dict, order: dict) -> dict:
    """
    Split delivery, service fee, and tip proportionally to each person's
    item total. Returns {participant: {delivery, service, tip, total}}.
    """
    fees = {
        "delivery": order["delivery_fee"],
        "service":  order["service_fee"],
        "driver_tip": order["driver_tip"],
    }
    allocations = {p: {"delivery": 0, "service": 0, "driver_tip": 0, "total": 0}
                   for p in participants}

    # Only split fees that are > 0
    for fee_name, fee_amount in fees.items():
        if fee_amount <= 0:
            continue
        # Participants with 0 items still get 0 fee allocation naturally
        split = _largest_remainder(fee_amount, item_totals)
        for p in participants:
            allocations[p][fee_name] += split.get(p, 0)

    for p in participants:
        allocations[p]["total"] = sum(
            allocations[p][k] for k in ("delivery", "service", "driver_tip")
        )

    return allocations


# ── Summary ───────────────────────────────────────────────────────────────────

def compute_totals(participants: list, assigned_items: list, fee_allocs: dict) -> dict:
    totals = {}
    for p in participants:
        items_total = sum(
            it["assignments"].get(p, 0) for it in assigned_items
        )
        fee_total = fee_allocs[p]["total"]
        totals[p] = {
            "items": items_total,
            "fees":  fee_total,
            "total": items_total + fee_total,
        }
    return totals


def print_summary(participants: list, totals: dict, order: dict) -> None:
    print(f"\n{SEP_DBL}")
    print(f"  SPLIT SUMMARY — {order['order_id']}")
    print(f"{SEP_DBL}")
    max_name = max(len(p) for p in participants)
    for p in participants:
        t = totals[p]
        print(
            f"  {p:<{max_name}}  Items: {t['items']:>8,} AMD"
            f"  Fees: {t['fees']:>6,} AMD"
            f"  TOTAL: {t['total']:>8,} AMD"
        )
    grand = sum(t["total"] for t in totals.values())
    print(f"{SEP}")
    print(f"  {'Grand total':<{max_name}}  {grand:>8,} AMD  "
          f"(order: {order['total_to_pay']:,} AMD)")
    if abs(grand - order["total_to_pay"]) > 2:
        print(f"  [!] Discrepancy of {abs(grand - order['total_to_pay']):,} AMD. "
              "Check for unassigned items or rounding.")
    print(f"{SEP_DBL}")


# ── Payment method ────────────────────────────────────────────────────────────

def collect_payment_info(participants: list, totals: dict) -> dict:
    """
    Ask about payment method and return a currency info dict.
    For revolut payments, asks for EUR/AMD rate, total EUR paid, and weekend flag,
    then computes each person's EUR share proportionally to their AMD total.
    """
    print(f"\n{SEP}")
    while True:
        try:
            method = input("  Payment method? ([C]ash / [R]evolut): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)
        if method in ("c", "cash"):
            return {"method": "cash"}
        if method in ("r", "revolut"):
            break
        print("  [!] Enter 'c' for cash or 'r' for revolut.")

    while True:
        try:
            rate = float(input("  EUR → AMD rate? (e.g. 411.50): ").strip())
            if rate > 0:
                break
        except (ValueError, EOFError):
            pass
        except KeyboardInterrupt:
            print("\nAborted.")
            sys.exit(0)
        print("  [!] Enter a positive number.")

    while True:
        try:
            eur_paid = float(input("  Total EUR paid (as shown in Revolut): ").strip())
            if eur_paid > 0:
                break
        except (ValueError, EOFError):
            pass
        except KeyboardInterrupt:
            print("\nAborted.")
            sys.exit(0)
        print("  [!] Enter a positive number.")

    while True:
        try:
            wk = input("  Weekend purchase? ([Y]es / [N]o): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)
        if wk in ("y", "yes"):
            is_weekend = True
            break
        if wk in ("n", "no"):
            is_weekend = False
            break
        print("  [!] Enter 'y' or 'n'.")

    while True:
        try:
            fu = input("  Exchange fair usage fee? ([Y]es / [N]o): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)
        if fu in ("y", "yes"):
            is_fair_usage = True
            break
        if fu in ("n", "no"):
            is_fair_usage = False
            break
        print("  [!] Enter 'y' or 'n'.")

    # Weekend adds 1% on top of base; fair usage adds another 1% on top of base.
    # Both fees are calculated from eur_paid independently and then summed.
    eur_fee       = round(eur_paid * 0.01, 4) if is_weekend else 0.0
    eur_fair_usage_fee = round(eur_paid * 0.01, 4) if is_fair_usage else 0.0
    eur_effective = round(eur_paid + eur_fee + eur_fair_usage_fee, 4)

    # Distribute EUR proportionally to each person's AMD total.
    # Use largest-remainder in euro-cents so sum == eur_effective exactly.
    total_amd = sum(t["total"] for t in totals.values())
    if total_amd > 0:
        eur_cents_total = round(eur_effective * 100)
        raw_cents = {p: totals[p]["total"] / total_amd * eur_cents_total for p in participants}
        floored   = {p: int(v) for p, v in raw_cents.items()}
        remainder = eur_cents_total - sum(floored.values())
        for p in sorted(participants, key=lambda p: -(raw_cents[p] % 1)):
            if remainder <= 0:
                break
            floored[p] += 1
            remainder  -= 1
        eur_per_person = {p: round(floored[p] / 100, 2) for p in participants}
    else:
        eur_per_person = {p: 0.0 for p in participants}

    # Print EUR summary
    print(f"\n{SEP}")
    print(f"  REVOLUT PAYMENT SUMMARY")
    print(f"  Rate         : {rate:,.2f} AMD/EUR")
    fees_desc = []
    if is_weekend:
        fees_desc.append(f"1% weekend (€{eur_fee:.2f})")
    if is_fair_usage:
        fees_desc.append(f"1% fair usage (€{eur_fair_usage_fee:.2f})")
    if fees_desc:
        print(f"  Paid         : €{eur_paid:.2f}  +  {' + '.join(fees_desc)}  =  €{eur_effective:.2f} total")
    else:
        print(f"  Paid         : €{eur_paid:.2f}  (no exchange fees)")
    print(f"  Per person:")
    for p in participants:
        print(f"    {p}: €{eur_per_person[p]:.2f}")

    return {
        "method":              "revolut",
        "rate":                rate,
        "eur_paid":            eur_paid,
        "is_weekend":          is_weekend,
        "eur_fee":             eur_fee,
        "is_fair_usage":       is_fair_usage,
        "eur_fair_usage_fee":  eur_fair_usage_fee,
        "eur_effective":       eur_effective,
        "eur_per_person":      eur_per_person,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    load_dotenv(ENV_PATH)

    if len(sys.argv) < 2:
        print("Usage: python tools/split_basket.py <order_id>")
        print("       python tools/split_basket.py KM0029977560")
        sys.exit(1)

    order_id = sys.argv[1].strip()
    order_path = TMP_DIR / f"order_{order_id}.json"

    if not order_path.exists():
        print(f"Order cache not found: {order_path}")
        print(f"Run: python tools/fetch_order.py")
        sys.exit(1)

    order = json.loads(order_path.read_text())

    # ── Participants ────────────────────────────────────────────────────────
    defaults = [p.strip() for p in os.getenv("DEFAULT_PARTICIPANTS", "Me,Mahdi,Amir").split(",") if p.strip()]
    print(f"\n{SEP_DBL}")
    print(f"  SPLIT BASKET — {order_id}")
    print(f"{SEP_DBL}")
    print(f"  Default participants: {', '.join(defaults)}")
    try:
        temp_raw = input("  Temporary participants? (names comma-separated, or Enter to skip): ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        sys.exit(0)

    temp_participants = [p.strip() for p in temp_raw.split(",") if p.strip()] if temp_raw else []
    participants = defaults + temp_participants

    if temp_participants:
        print(f"  Active participants: {', '.join(participants)}")

    # ── Order overview ──────────────────────────────────────────────────────
    active_items = [it for it in order["items"] if not it["is_canceled"]]
    print(f"\n  Order     : {order['order_id']}  |  {order.get('status_label', '')}")
    print(f"  Items     : {len(active_items)} active")
    fees = []
    if order["delivery_fee"]: fees.append(f"Delivery {order['delivery_fee']:,}")
    if order["service_fee"]:  fees.append(f"Service {order['service_fee']:,}")
    if order["driver_tip"]:   fees.append(f"Tip {order['driver_tip']:,}")
    if fees:
        print(f"  Fees      : {' | '.join(fees)} AMD")
    print(f"  Total     : {order['total_to_pay']:,} AMD")

    print(f"\n  Walking through {len(active_items)} items. Canceled items are skipped.")
    input("  Press Enter to begin ...")

    # ── Item-by-item assignment ─────────────────────────────────────────────
    assigned_items = assign_items(order["items"], participants)

    # ── Fee allocation ──────────────────────────────────────────────────────
    item_totals = {
        p: sum(it["assignments"].get(p, 0) for it in assigned_items)
        for p in participants
    }
    fee_allocs = allocate_fees(participants, item_totals, order)
    totals     = compute_totals(participants, assigned_items, fee_allocs)

    print_summary(participants, totals, order)

    # ── Payment method ───────────────────────────────────────────────────────
    currency = collect_payment_info(participants, totals)

    # ── Save ────────────────────────────────────────────────────────────────
    split_data = {
        "order_id":     order_id,
        "split_date":   datetime.now(tz=timezone.utc).isoformat(),
        "participants": participants,
        "items":        assigned_items,
        "fees": {
            "delivery":   order["delivery_fee"],
            "service":    order["service_fee"],
            "driver_tip": order["driver_tip"],
        },
        "fee_allocations": fee_allocs,
        "totals":       totals,
        "currency":     currency,
        "order_total":  order["total_to_pay"],
        "order_meta":   {
            "create_date":   order.get("create_date"),
            "status_label":  order.get("status_label"),
            "branch_address": order.get("branch_address"),
            "payment_label": order.get("payment_label"),
            "is_delivery":   order.get("is_delivery"),
        },
    }

    out_path = TMP_DIR / f"split_{order_id}.json"
    out_path.write_text(json.dumps(split_data, indent=2, ensure_ascii=False, default=str))
    print(f"\n  Saved: {out_path}")
    print(f"  Next : python tools/generate_report.py {order_id}")


if __name__ == "__main__":
    main()
