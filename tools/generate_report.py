#!/usr/bin/env python3
"""
Generate a Google Sheets report from a split JSON file.

Each order gets its own tab named "Order {order_id}".
A _Summary tab is created/updated with one row per order.

Uses Application Default Credentials (gcloud auth application-default login).
If GOOGLE_SHEET_ID is not set in .env, a new spreadsheet is created and the
ID is written back automatically.

Usage:
  python tools/generate_report.py <order_id>
  python tools/generate_report.py KM0029977560
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv, set_key

ROOT     = Path(__file__).parent.parent
ENV_PATH = ROOT / ".env"
TMP_DIR  = ROOT / "data"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── Colours (RGB 0–1 floats) ──────────────────────────────────────────────────
def _rgb(r, g, b):
    return {"red": r / 255, "green": g / 255, "blue": b / 255}

C_HEADER_DARK  = _rgb(26,  35, 126)   # indigo 900 — order header bg
C_HEADER_MID   = _rgb(57,  73, 171)   # indigo 700 — table column header bg
C_ROW_ALT      = _rgb(232, 234, 246)  # indigo 50  — alternating item rows
C_FEE_HEADER   = _rgb(40,  53, 147)   # indigo 800 — fee block header
C_TOTAL_BG     = _rgb(232, 245, 233)  # green  50  — per-person total row bg
C_TOTAL_BOLD   = _rgb(27,  94,  32)   # green  900 — total row text
C_WHITE        = _rgb(255, 255, 255)
C_SUMMARY_HDR  = _rgb(69, 90, 100)    # blue grey 700


# ── gspread helpers ───────────────────────────────────────────────────────────

def _get_gc():
    try:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        import gspread
    except ImportError:
        print("Missing packages. Run: .venv/bin/pip install gspread google-auth")
        sys.exit(1)

    try:
        creds, _ = google.auth.default(scopes=SCOPES)
    except Exception:
        print(
            "Google Application Default Credentials not found.\n"
            "Run: gcloud auth application-default login\n"
            "Then retry."
        )
        sys.exit(1)

    gc = gspread.Client(auth=creds)
    gc.session = AuthorizedSession(creds)
    return gc


def _open_or_create_spreadsheet(gc, sheet_id: str):
    import gspread
    if sheet_id:
        try:
            return gc.open_by_key(sheet_id)
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"Spreadsheet {sheet_id} not found. Creating a new one ...")

    sh = gc.create("Yerevan City Orders")
    new_id = sh.id
    set_key(str(ENV_PATH), "GOOGLE_SHEET_ID", new_id)
    print(f"Created spreadsheet: https://docs.google.com/spreadsheets/d/{new_id}")
    print("GOOGLE_SHEET_ID saved to .env")
    return sh


def _get_or_create_worksheet(sh, title: str, rows: int = 200, cols: int = 30):
    import gspread
    try:
        ws = sh.worksheet(title)
        print(f"Tab '{title}' already exists — overwriting ...")
        ws.clear()
        return ws
    except gspread.exceptions.WorksheetNotFound:
        return sh.add_worksheet(title=title, rows=rows, cols=cols)


# ── Formatting request builders ───────────────────────────────────────────────

def _bg_req(ws_id: int, start_row: int, end_row: int, start_col: int, end_col: int, color: dict):
    return {
        "repeatCell": {
            "range": {
                "sheetId": ws_id,
                "startRowIndex": start_row, "endRowIndex": end_row,
                "startColumnIndex": start_col, "endColumnIndex": end_col,
            },
            "cell": {"userEnteredFormat": {"backgroundColor": color}},
            "fields": "userEnteredFormat.backgroundColor",
        }
    }


def _text_req(ws_id: int, start_row: int, end_row: int, start_col: int, end_col: int,
              bold=False, color: dict = None, size: int = None, h_align: str = None):
    fmt = {}
    if bold is not None or color or size:
        tf = {}
        if bold is not None: tf["bold"] = bold
        if color:            tf["foregroundColor"] = color
        if size:             tf["fontSize"] = size
        fmt["textFormat"] = tf
    if h_align:
        fmt["horizontalAlignment"] = h_align
    return {
        "repeatCell": {
            "range": {
                "sheetId": ws_id,
                "startRowIndex": start_row, "endRowIndex": end_row,
                "startColumnIndex": start_col, "endColumnIndex": end_col,
            },
            "cell": {"userEnteredFormat": fmt},
            "fields": "userEnteredFormat(" + ",".join(fmt.keys()) + ")",
        }
    }


def _number_fmt_req(ws_id: int, start_row: int, end_row: int, start_col: int, end_col: int,
                    pattern: str = "#,##0"):
    return {
        "repeatCell": {
            "range": {
                "sheetId": ws_id,
                "startRowIndex": start_row, "endRowIndex": end_row,
                "startColumnIndex": start_col, "endColumnIndex": end_col,
            },
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": pattern}}},
            "fields": "userEnteredFormat.numberFormat",
        }
    }


def _freeze_req(ws_id: int, rows: int = 0, cols: int = 0):
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": ws_id,
                "gridProperties": {"frozenRowCount": rows, "frozenColumnCount": cols},
            },
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
        }
    }


def _col_width_req(ws_id: int, col_idx: int, width_px: int):
    return {
        "updateDimensionProperties": {
            "range": {
                "sheetId": ws_id,
                "dimension": "COLUMNS",
                "startIndex": col_idx,
                "endIndex": col_idx + 1,
            },
            "properties": {"pixelSize": width_px},
            "fields": "pixelSize",
        }
    }


def _borders_req(ws_id: int, start_row: int, end_row: int, start_col: int, end_col: int):
    solid = {"style": "SOLID", "color": _rgb(189, 189, 189)}
    return {
        "updateBorders": {
            "range": {
                "sheetId": ws_id,
                "startRowIndex": start_row, "endRowIndex": end_row,
                "startColumnIndex": start_col, "endColumnIndex": end_col,
            },
            "bottom": solid, "top": solid, "left": solid, "right": solid,
            "innerHorizontal": solid, "innerVertical": solid,
        }
    }


# ── Order tab ─────────────────────────────────────────────────────────────────

def _write_order_tab(sh, split: dict) -> None:
    order_id    = split["order_id"]
    participants = split["participants"]
    items       = split["items"]
    fees        = split["fees"]
    fee_allocs  = split["fee_allocations"]
    totals      = split["totals"]
    meta        = split.get("order_meta", {})
    currency    = split.get("currency", {"method": "cash"})
    is_revolut  = currency.get("method") == "revolut"
    n_p         = len(participants)

    tab_title = f"Order {order_id}"
    ws = _get_or_create_worksheet(sh, tab_title, rows=300, cols=20 + n_p)
    ws_id = ws.id

    # ── Column layout ────────────────────────────────────────────────────────
    # A(0)  B(1)      C(2)  D(3)   E(4)        F(5)     G(6)       H(7)
    # #     Item      Qty   Unit   Unit Price   Total    Discount   Net
    # then one col per participant, then Method
    P_START = 8               # first participant column index
    P_END   = P_START + n_p   # exclusive
    COL_METHOD = P_END        # last column
    TOTAL_COLS = COL_METHOD + 1

    # ── Block A: Order header (rows 0–3, 0-indexed) ──────────────────────────
    date_str = ""
    if meta.get("create_date"):
        try:
            date_str = datetime.fromisoformat(
                str(meta["create_date"]).replace("Z", "+00:00")
            ).strftime("%Y-%m-%d")
        except Exception:
            date_str = str(meta["create_date"])[:10]

    delivery_str = "Yes" if meta.get("is_delivery") else "No"
    total_fees = fees["delivery"] + fees["service"] + fees["driver_tip"]
    items_subtotal = sum(it["net_price"] for it in items if not it["is_canceled"])

    if is_revolut:
        eur_paid      = currency.get("eur_paid", 0)
        eur_effective = currency.get("eur_effective", eur_paid)
        eur_fee       = currency.get("eur_fee", 0)
        rate          = currency.get("rate", 0)
        weekend_label = "Yes (1% fee applied)" if currency.get("is_weekend") else "No"
        revolut_row   = [
            "Payment:", "Revolut", "",
            "EUR paid:", eur_paid, "",
            f"Weekend:", weekend_label, "",
            "EUR effective:", eur_effective, "",
            "Fee (EUR):", eur_fee, "",
            "Rate (AMD/EUR):", rate,
        ]
    else:
        revolut_row = None

    header_rows = [
        [f"Order {order_id}", "", "Date:", date_str, "", "Status:", meta.get("status_label", ""), "", f"Delivery: {delivery_str}"],
        ["Branch:", meta.get("branch_address", "N/A"), "", "", "Payment:", meta.get("payment_label", ""), "", "", ""],
    ]
    if revolut_row:
        header_rows.append(revolut_row)
    header_rows += [
        [""],
        ["Items Subtotal:", items_subtotal, "", "Delivery Fee:", fees["delivery"], "Service Fee:", fees["service"],
         "Tip:", fees["driver_tip"], "TOTAL:", split["order_total"]],
        [""],
    ]
    ws.update("A1", header_rows)

    # ── Block B: Item table ──────────────────────────────────────────────────
    COL_HEADER_ROW = len(header_rows)  # 0-indexed; shifts by 1 when revolut row present
    item_headers = ["#", "Item", "Qty", "Unit", "Unit Price", "Total", "Discount", "Net"] \
                   + participants + ["Method"]
    data_rows = [item_headers]

    for seq, it in enumerate([i for i in items if not i["is_canceled"]], start=1):
        row = [
            seq,
            it["name"],
            it["quantity"],
            it.get("unit") or "",
            it["unit_price"],
            it["total_price"],
            it["discount"] if it["discount"] else "",
            it["net_price"],
        ]
        for p in participants:
            row.append(it["assignments"].get(p, 0) or "")
        row.append(it.get("split_method", ""))
        data_rows.append(row)

    item_start_row = COL_HEADER_ROW   # 0-indexed
    ws.update(f"A{item_start_row + 1}", data_rows)

    n_active = len([i for i in items if not i["is_canceled"]])
    item_data_end = item_start_row + n_active   # last item row (0-indexed, inclusive)

    # ── Block C: Fee allocation ──────────────────────────────────────────────
    fee_section_row = item_data_end + 2   # skip one blank row

    fee_header_cells = ["Fee Allocation"] + [""] * (n_p - 1 + 8)
    fee_col_header   = ["", "Delivery", "Service", "Tip", "Fee Total"] + [""] * 5
    ws.update(f"A{fee_section_row + 1}", [fee_header_cells])
    ws.update(f"A{fee_section_row + 2}", [fee_col_header])

    fee_rows = []
    for p in participants:
        fa = fee_allocs.get(p, {})
        fee_rows.append([p, fa.get("delivery", 0), fa.get("service", 0),
                         fa.get("driver_tip", 0), fa.get("total", 0)])
    ws.update(f"A{fee_section_row + 3}", fee_rows)

    # ── Block D: Final totals ────────────────────────────────────────────────
    total_section_row = fee_section_row + 2 + len(participants) + 2

    total_header  = ["TOTAL OWED"] + [""] * (n_p - 1 + 8)
    if is_revolut:
        total_col_hdr = ["", "Items (AMD)", "Fees (AMD)", "TOTAL (AMD)", "TOTAL (EUR)"]
        eur_pp = currency.get("eur_per_person", {})
    else:
        total_col_hdr = ["", "Items", "Fees", "TOTAL"]
        eur_pp = {}
    ws.update(f"A{total_section_row + 1}", [total_header])
    ws.update(f"A{total_section_row + 2}", [total_col_hdr])

    total_rows = []
    for p in participants:
        t = totals.get(p, {})
        row = [p, t.get("items", 0), t.get("fees", 0), t.get("total", 0)]
        if is_revolut:
            row.append(eur_pp.get(p, 0))
        total_rows.append(row)
    ws.update(f"A{total_section_row + 3}", total_rows)

    # ── Formatting ───────────────────────────────────────────────────────────
    requests = []

    # Order header block bg (rows 0–3)
    requests.append(_bg_req(ws_id, 0, 2, 0, TOTAL_COLS, C_HEADER_DARK))
    requests.append(_text_req(ws_id, 0, 2, 0, TOTAL_COLS, bold=True, color=C_WHITE))
    requests.append(_bg_req(ws_id, 3, 4, 0, TOTAL_COLS, _rgb(21, 101, 192)))
    requests.append(_text_req(ws_id, 3, 4, 0, TOTAL_COLS, bold=True, color=C_WHITE))

    # Item table column header (row COL_HEADER_ROW)
    requests.append(_bg_req(ws_id, item_start_row, item_start_row + 1, 0, TOTAL_COLS, C_HEADER_MID))
    requests.append(_text_req(ws_id, item_start_row, item_start_row + 1, 0, TOTAL_COLS,
                               bold=True, color=C_WHITE, h_align="CENTER"))
    requests.append(_freeze_req(ws_id, rows=item_start_row + 1, cols=2))

    # Item rows: alternating background
    for idx in range(n_active):
        row_idx = item_start_row + 1 + idx
        if idx % 2 == 1:
            requests.append(_bg_req(ws_id, row_idx, row_idx + 1, 0, TOTAL_COLS, C_ROW_ALT))

    # Number format for price columns (unit price, total, discount, net, participant cols)
    price_col_start = 4  # E = unit price
    requests.append(_number_fmt_req(
        ws_id,
        item_start_row + 1, item_data_end + 1,
        price_col_start, TOTAL_COLS - 1,  # exclude Method column
    ))

    # Borders on item table
    requests.append(_borders_req(
        ws_id,
        item_start_row, item_data_end + 1,
        0, TOTAL_COLS,
    ))

    # Fee allocation section
    requests.append(_bg_req(ws_id, fee_section_row, fee_section_row + 1, 0, TOTAL_COLS, C_FEE_HEADER))
    requests.append(_text_req(ws_id, fee_section_row, fee_section_row + 1, 0, TOTAL_COLS,
                               bold=True, color=C_WHITE))
    requests.append(_bg_req(ws_id, fee_section_row + 1, fee_section_row + 2, 0, 5, _rgb(48, 63, 159)))
    requests.append(_text_req(ws_id, fee_section_row + 1, fee_section_row + 2, 0, 5,
                               bold=True, color=C_WHITE))
    requests.append(_number_fmt_req(ws_id, fee_section_row + 2,
                                    fee_section_row + 2 + len(participants), 1, 5))

    # Totals section
    total_data_cols = 5 if is_revolut else 4  # includes EUR column for revolut
    requests.append(_bg_req(ws_id, total_section_row, total_section_row + 1, 0, TOTAL_COLS, C_FEE_HEADER))
    requests.append(_text_req(ws_id, total_section_row, total_section_row + 1, 0, TOTAL_COLS,
                               bold=True, color=C_WHITE, size=11))
    requests.append(_bg_req(ws_id, total_section_row + 1, total_section_row + 2, 0, total_data_cols, _rgb(48, 63, 159)))
    requests.append(_text_req(ws_id, total_section_row + 1, total_section_row + 2, 0, total_data_cols,
                               bold=True, color=C_WHITE))

    # Highlight each person's TOTAL OWED (AMD) cell with green bg
    for idx in range(len(participants)):
        r = total_section_row + 2 + idx
        requests.append(_bg_req(ws_id, r, r + 1, 3, 4, C_TOTAL_BG))
        requests.append(_text_req(ws_id, r, r + 1, 3, 4, bold=True, color=C_TOTAL_BOLD))
        if is_revolut:
            # EUR column highlighted in a warm amber
            requests.append(_bg_req(ws_id, r, r + 1, 4, 5, _rgb(255, 248, 225)))
            requests.append(_text_req(ws_id, r, r + 1, 4, 5, bold=True, color=_rgb(230, 81, 0)))

    # AMD number format for items/fees/total columns
    requests.append(_number_fmt_req(ws_id, total_section_row + 2,
                                    total_section_row + 2 + len(participants), 1, 4))
    # EUR number format (2 decimal places) for EUR column
    if is_revolut:
        requests.append(_number_fmt_req(ws_id, total_section_row + 2,
                                        total_section_row + 2 + len(participants), 4, 5,
                                        pattern="#,##0.00"))

    # Column widths
    col_widths = {0: 40, 1: 250, 2: 50, 3: 50, 4: 100, 5: 90, 6: 90, 7: 90}
    for col_idx in range(P_START, P_END):
        col_widths[col_idx] = 100
    for col_idx, px in col_widths.items():
        requests.append(_col_width_req(ws_id, col_idx, px))

    # Row 1 (order ID) larger font
    requests.append(_text_req(ws_id, 0, 1, 0, 1, bold=True, color=C_WHITE, size=13))

    sh.batch_update({"requests": requests})

    url = f"https://docs.google.com/spreadsheets/d/{sh.id}#gid={ws.id}"
    print(f"Order tab written: {url}")
    return ws


# ── Summary tab ───────────────────────────────────────────────────────────────

def _update_summary_tab(sh, split: dict) -> None:
    import gspread

    SUMMARY_TITLE = "_Summary"
    participants  = split["participants"]
    totals        = split["totals"]
    meta          = split.get("order_meta", {})

    date_str = ""
    if meta.get("create_date"):
        try:
            date_str = datetime.fromisoformat(
                str(meta["create_date"]).replace("Z", "+00:00")
            ).strftime("%Y-%m-%d")
        except Exception:
            date_str = str(meta["create_date"])[:10]

    try:
        ws_sum = sh.worksheet(SUMMARY_TITLE)
    except gspread.exceptions.WorksheetNotFound:
        ws_sum = sh.add_worksheet(SUMMARY_TITLE, rows=500, cols=20)
        # Move summary to first position
        sh.reorder_worksheets([ws_sum] + [w for w in sh.worksheets() if w.title != SUMMARY_TITLE])
        headers = (
            ["Order ID", "Date", "Status", "Branch", "Total AMD", "# Items"]
            + participants
            + ["Split Date"]
        )
        ws_sum.update("A1", [headers])
        ws_id_sum = ws_sum.id
        fmt_reqs = [
            _bg_req(ws_id_sum, 0, 1, 0, len(headers), C_SUMMARY_HDR),
            _text_req(ws_id_sum, 0, 1, 0, len(headers), bold=True, color=C_WHITE),
            _freeze_req(ws_id_sum, rows=1),
        ]
        sh.batch_update({"requests": fmt_reqs})

    # Check if row for this order already exists → update in-place
    order_id = split["order_id"]
    all_vals = ws_sum.get_all_values()
    existing_row = None
    for i, row in enumerate(all_vals[1:], start=2):  # 1-indexed, skip header
        if row and row[0] == order_id:
            existing_row = i
            break

    n_items = len([i for i in split["items"] if not i.get("is_canceled")])
    row_data = [
        order_id,
        date_str,
        meta.get("status_label", ""),
        meta.get("branch_address", ""),
        split["order_total"],
        n_items,
    ] + [totals.get(p, {}).get("total", 0) for p in participants] + [
        datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ]

    if existing_row:
        ws_sum.update(f"A{existing_row}", [row_data])
    else:
        ws_sum.append_row(row_data, value_input_option="USER_ENTERED")

    print(f"_Summary tab updated.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    load_dotenv(ENV_PATH)

    if len(sys.argv) < 2:
        print("Usage: python tools/generate_report.py <order_id>")
        sys.exit(1)

    order_id   = sys.argv[1].strip()
    split_path = TMP_DIR / f"split_{order_id}.json"

    if not split_path.exists():
        print(f"Split file not found: {split_path}")
        print(f"Run: python tools/split_basket.py {order_id}")
        sys.exit(1)

    split = json.loads(split_path.read_text())

    print("Connecting to Google Sheets ...")
    gc = _get_gc()

    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    sh = _open_or_create_spreadsheet(gc, sheet_id)

    print(f"Writing order tab ...")
    _write_order_tab(sh, split)

    print("Updating summary tab ...")
    _update_summary_tab(sh, split)

    url = f"https://docs.google.com/spreadsheets/d/{sh.id}"
    print(f"\nDone. Open your report:\n{url}")


if __name__ == "__main__":
    main()
