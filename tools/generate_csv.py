#!/usr/bin/env python3
"""
Generate a Tricount-compatible CSV from a split JSON file.

Format mirrors the tricount tracking sheet:
  product | price | services | <weight per person…> | <AMD per person…>
  + footer: per-person AMD totals, grand total, Revolut section if applicable.

Usage:
  python tools/generate_csv.py <order_id>
  python tools/generate_csv.py KM0029977560
"""

import csv
import json
import sys
from pathlib import Path

ROOT    = Path(__file__).parent.parent
TMP_DIR = ROOT / "data"


# ── Weights and exact decimal amounts ────────────────────────────────────────

def display_weights(weights: dict, participants: list) -> list:
    """Return the stored weights exactly as entered — no transformation."""
    return [weights.get(p, 0) for p in participants]


def exact_amounts(weights: dict, participants: list, net_price: float) -> list:
    """
    Compute per-person amounts as 2-decimal floats summing exactly to net_price.

    Formula: amount_x = net_price × w_x / Σw
    Uses largest-remainder in cents so the total is always exact.

    Examples (net_price=694, equal weights 1,1,1):
      694 × 1/3 = 231.33 | 231.33 | 231.34
    """
    total_w = sum(weights.get(p, 0) for p in participants)
    if total_w == 0:
        return [0.0] * len(participants)
    cents_total = round(net_price * 100)
    raw_cents   = {p: weights.get(p, 0) / total_w * cents_total for p in participants}
    floored     = {p: int(v) for p, v in raw_cents.items()}
    remainder   = cents_total - sum(floored.values())
    for p in sorted(participants, key=lambda p: -(raw_cents[p] % 1)):
        if remainder <= 0:
            break
        floored[p] += 1
        remainder  -= 1
    return [round(floored[p] / 100, 2) for p in participants]


# ── Shared row layout ─────────────────────────────────────────────────────────
# Extracted so generate_receipt_image.py can render the exact same rows as an
# image instead of a spreadsheet — same math, same column layout, no
# duplicated logic. Column layout:
#   0: product  1: price  2: services
#   3…3+n_p-1 : weight columns (one per participant)
#   3+n_p…3+2n_p-1 : AMD amount columns (one per participant)
#   3+2n_p : note column (revolut info)

def build_report_rows(split: dict) -> list[list]:
    """Returns the full list of rows (header, items, totals, optional Revolut
    section) exactly as written to the CSV — one row per output line."""
    participants = split["participants"]
    items        = split["items"]
    totals       = split["totals"]
    currency     = split.get("currency", {"method": "cash"})
    is_revolut   = currency.get("method") == "revolut"
    order_total  = split["order_total"]

    n_p     = len(participants)
    p_lower = [p.lower() for p in participants]

    N_BASE      = 3
    AMT_START   = N_BASE + n_p          # first AMD amount column index
    NOTE_COL    = N_BASE + 2 * n_p      # column after last AMD amount
    CENTER_AMT  = AMT_START + n_p // 2  # middle of AMD amount block
    TOTAL_DATA  = N_BASE + 2 * n_p

    def _row(col_vals: dict) -> list:
        row = [""] * (TOTAL_DATA + 1)
        for col, val in col_vals.items():
            row[col] = val
        return row

    def _amt_row(amounts: list, note: str = "") -> list:
        row = [""] * (TOTAL_DATA + 1)
        for i, val in enumerate(amounts):
            row[AMT_START + i] = val
        if note:
            row[NOTE_COL] = note
        return row

    rows = [["product", "price", "services"] + p_lower + p_lower + [""]]

    for it in items:
        if it.get("is_canceled"):
            continue
        aw = it.get("assignment_weights")
        if not aw:
            # Fallback for splits without stored weights: treat equal share
            # for each participant who received a non-zero amount
            aw = {p: (1 if it["assignments"].get(p, 0) > 0 else 0)
                  for p in participants}
        weights = display_weights(aw, participants)
        amounts = exact_amounts(aw, participants, it["net_price"])
        rows.append([it["name"], it.get("price", it["net_price"]), it.get("service", 0)] + weights + amounts + [""])

    rows.append([""] * (TOTAL_DATA + 1))  # blank separator

    amd_totals = [totals[p]["total"] for p in participants]
    rows.append(_amt_row(amd_totals))

    note = "double check" if is_revolut else ""
    grand_row = _row({CENTER_AMT: order_total})
    if note:
        grand_row[NOTE_COL] = note
    rows.append(grand_row)

    if is_revolut:
        eur_paid           = currency.get("eur_paid", 0)
        eur_fee            = currency.get("eur_fee", 0)
        eur_fair_usage_fee = currency.get("eur_fair_usage_fee", 0)
        rate               = currency.get("rate", 0)
        eur_pp             = currency.get("eur_per_person", {})

        for val in [eur_paid, rate, order_total]:
            rows.append(_row({NOTE_COL: val}))

        rows.append([""] * (TOTAL_DATA + 1))

        label_row = [""] * (TOTAL_DATA + 1)
        label_row[AMT_START] = "weekend fee"
        rows.append(label_row)
        rows.append(_row({CENTER_AMT: eur_fee}))

        label_row = [""] * (TOTAL_DATA + 1)
        label_row[AMT_START] = "fair usage fee"
        rows.append(label_row)
        rows.append(_row({CENTER_AMT: eur_fair_usage_fee}))

        eur_amounts = [eur_pp.get(p, 0) for p in participants]
        rows.append(_amt_row(eur_amounts))

    return rows


# ── CSV writer ────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tools/generate_csv.py <order_id>")
        sys.exit(1)

    order_id   = sys.argv[1].strip()
    split_path = TMP_DIR / f"split_{order_id}.json"

    if not split_path.exists():
        print(f"Split file not found: {split_path}")
        print(f"Run: python tools/split_basket.py {order_id}")
        sys.exit(1)

    split = json.loads(split_path.read_text())
    rows  = build_report_rows(split)

    out_path = TMP_DIR / f"report_{order_id}.csv"
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerows(rows)

    print(f"Report saved : {out_path}")
    print(f"Open         : open \"{out_path}\"")


if __name__ == "__main__":
    main()
