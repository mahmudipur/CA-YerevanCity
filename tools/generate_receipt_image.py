#!/usr/bin/env python3
"""
Render the same rows generate_csv.py writes to CSV as a single PNG table
instead — meant to replace "open the CSV, screenshot it" for pasting into
Tricount as a receipt image. One image, sized to fit every row, so there's
never a scroll/screenshot step on any device (the whole reason this exists:
a laptop screenshot happens to fit the CSV in one shot, a phone screenshot
of the same spreadsheet doesn't).

Reuses generate_csv.build_report_rows() — same math, same column layout,
no duplicated logic; this is purely a different renderer for those rows.

Usage:
  python tools/generate_receipt_image.py <order_id>
  python tools/generate_receipt_image.py KM0029977560
"""

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from generate_csv import build_report_rows  # noqa: E402

TMP_DIR = ROOT / "data"

# ── Layout constants ──────────────────────────────────────────────────────────
PADDING = 12
CELL_PAD_X = 10
CELL_PAD_Y = 6
FONT_SIZE = 18
MARGIN = 20
BORDER_COLOR = (210, 210, 214)
HEADER_BG = (235, 235, 240)
TOTALS_BG = (245, 240, 220)
TEXT_COLOR = (30, 30, 34)
BG_COLOR = (255, 255, 255)
# Columns 0/1/2 (product/price/services) are left/right-aligned text;
# everything from column 3 onward (weights, amounts, note) is numeric/
# short and right-aligned, matching how a spreadsheet naturally reads.
RIGHT_ALIGN_FROM = 1


def _fmt_cell(value) -> str:
    if value == "" or value is None:
        return ""
    if isinstance(value, float):
        # Trim trailing .0 for whole numbers, keep 2dp otherwise (matches
        # the CSV's own exact_amounts() output).
        return f"{value:,.2f}".rstrip("0").rstrip(".") if value % 1 else f"{value:,.0f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def render_receipt_image(split: dict, out_path: Path) -> Path:
    raw_rows = build_report_rows(split)
    n_cols = max(len(r) for r in raw_rows)
    cells = [[_fmt_cell(v) for v in row] + [""] * (n_cols - len(row)) for row in raw_rows]

    font = ImageFont.load_default(size=FONT_SIZE)
    header_font = ImageFont.load_default(size=FONT_SIZE)

    scratch = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(scratch)

    def text_w(s: str, f) -> int:
        if not s:
            return 0
        box = draw.textbbox((0, 0), s, font=f)
        return box[2] - box[0]

    col_widths = [0] * n_cols
    for r_idx, row in enumerate(cells):
        f = header_font if r_idx == 0 else font
        for c_idx, val in enumerate(row):
            col_widths[c_idx] = max(col_widths[c_idx], text_w(val, f))
    col_widths = [w + 2 * CELL_PAD_X for w in col_widths]

    row_height = FONT_SIZE + 2 * CELL_PAD_Y
    table_w = sum(col_widths)
    table_h = row_height * len(cells)

    title = split.get("session_name") or split.get("order_id", "")
    title_h = FONT_SIZE + 3 * CELL_PAD_Y if title else 0

    img_w = table_w + 2 * MARGIN
    img_h = table_h + title_h + 2 * MARGIN
    img = Image.new("RGB", (img_w, img_h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = MARGIN
    if title:
        title_font = ImageFont.load_default(size=FONT_SIZE + 6)
        draw.text((MARGIN, y), str(title), font=title_font, fill=TEXT_COLOR)
        y += title_h

    # Rows that are ~entirely blank except one/two cells (totals, Revolut
    # notes) get a highlight background so they read as "summary", not
    # "another item".
    blank_heavy_from = 1 + len([it for it in split.get("items", []) if not it.get("is_canceled")])

    for r_idx, row in enumerate(cells):
        row_bg = HEADER_BG if r_idx == 0 else (TOTALS_BG if r_idx >= blank_heavy_from else BG_COLOR)
        x = MARGIN
        f = header_font if r_idx == 0 else font
        for c_idx, val in enumerate(row):
            w = col_widths[c_idx]
            draw.rectangle([x, y, x + w, y + row_height], fill=row_bg, outline=BORDER_COLOR)
            if val:
                tw = text_w(val, f)
                if c_idx >= RIGHT_ALIGN_FROM:
                    tx = x + w - CELL_PAD_X - tw
                else:
                    tx = x + CELL_PAD_X
                draw.text((tx, y + CELL_PAD_Y), val, font=f, fill=TEXT_COLOR)
            x += w
        y += row_height

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG")
    return out_path


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python tools/generate_receipt_image.py <order_id>")
        sys.exit(1)

    order_id = sys.argv[1].strip()
    split_path = TMP_DIR / f"split_{order_id}.json"
    if not split_path.exists():
        print(f"Split file not found: {split_path}")
        print(f"Run: python tools/split_basket.py {order_id}")
        sys.exit(1)

    split = json.loads(split_path.read_text())
    out_path = TMP_DIR / f"receipt_{order_id}.png"
    render_receipt_image(split, out_path)

    print(f"Image saved : {out_path}")
    print(f"Open        : open \"{out_path}\"")


if __name__ == "__main__":
    main()
