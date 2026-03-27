# Yerevan City Order Splitter

Split Yerevan City grocery orders (and any manual expense) item-by-item among a group, then export a Tricount-compatible CSV.

---

## What it does

| Step | Script | Purpose |
|---|---|---|
| 1 | `auth_yc.py` | Authenticate via phone OTP, save JWT to `.env` |
| 2 | `fetch_order.py` | Pull your latest YC order from the API, cache it locally |
| 3 | `split_basket.py` | Walk through each item interactively and assign it to people |
| 4 | `generate_csv.py` | Write a Tricount-compatible CSV report |

**Shortcut:** `run.py` chains all four steps into a single interactive session, and also supports manual expenses (restaurants, cafes, etc.).

---

## One-time setup

### 1. Create the virtual environment

```bash
cd /path/to/CA-YerevanCity
python3 -m venv .venv
.venv/bin/pip install python-dotenv requests
```

### 2. Create `.env`

Copy the template below and fill in your phone number:

```env
# Yerevan City API
YC_PHONE_LOCAL=55XXXXXX          # local format (no country code)
YC_PHONE_E164=+37455XXXXXX       # E.164 format

YC_DEVICE_ID=                    # leave empty — generated automatically on first auth
YC_JWT=                          # leave empty — filled by auth_yc.py

# Participants (comma-separated, order = column order in the CSV)
DEFAULT_PARTICIPANTS=Me,Mahdi,Amir

# Google Sheets (optional — only needed for generate_report.py)
GOOGLE_SHEET_ID=
```

### 3. Authenticate with Yerevan City

```bash
.venv/bin/python tools/auth_yc.py
```

You'll get an SMS OTP. Enter it. The JWT is written to `.env` automatically.

> **Re-run this any time you see "Unauthorized" errors.** The JWT lasts a few weeks.

---

## Running a split

### Option A — one command (recommended)

```bash
.venv/bin/python tools/run.py
```

You'll be asked to choose:

```
────────────────────────────────────────────────────────────
  What would you like to split?
  [1] Yerevan City order
  [2] Manual expense  (restaurant, cafe, etc.)
────────────────────────────────────────────────────────────
  Choice:
```

- **Choice 1** fetches your latest YC order, runs the interactive splitter, and generates the CSV.
- **Choice 2** lets you enter items manually (name, price, optional service charge), then generates the CSV.

Add `--refresh` to force a fresh fetch even if the order is already cached:

```bash
.venv/bin/python tools/run.py --refresh
```

---

### Option B — step by step

```bash
# 1. Fetch latest order (cached to .tmp/order_<id>.json)
.venv/bin/python tools/fetch_order.py

# 2. Split items interactively (produces .tmp/split_<id>.json)
.venv/bin/python tools/split_basket.py KM0030XXXXXX

# 3. Generate CSV report (produces .tmp/report_<id>.csv)
.venv/bin/python tools/generate_csv.py KM0030XXXXXX

# 4. Open it
open .tmp/report_KM0030XXXXXX.csv
```

---

## Splitting items

For each item the tool shows:

```
────────────────────────────────────────────────────────────
  Item 3/12
  Milk 3.2%
  x2 pcs  ·  900 AMD/unit
  Net: 1,800 AMD
────────────────────────────────────────────────────────────
  Participants: Me, Mahdi, Amir
  Formats: Enter=all equal | me,mahdi | me:60%,mahdi:40% | me:1200,mahdi:600
  Assign >
```

### Assignment formats

| Input | Result |
|---|---|
| `Enter` (or `all`) | Equal split among everyone |
| `me` | 100% to Me |
| `me,mahdi` | Equal split between Me and Mahdi only |
| `me:60%,mahdi:40%` | Percentage split (must sum to 100%) |
| `me:1200,mahdi:600` | Fixed AMD amounts (must sum to item net price) |

Names are **case-insensitive** and support **prefix matching** (`m` → `Me` if unambiguous).

After all items are assigned, delivery/service/tip fees are distributed **proportionally** to each person's item total using the largest-remainder method (sum is always exact).

---

## Payment methods

At the end of each split you're asked how it was paid:

- **Cash** — nothing extra needed, saves and exits.
- **Revolut** — you'll be asked for:
  - EUR → AMD exchange rate (e.g. `411.50`)
  - Total EUR shown in Revolut
  - Whether it was a **weekend** purchase (Revolut adds a 1% exchange markup on weekends)

  The tool computes each person's EUR share and includes it in the CSV footer.

---

## CSV output format

| Columns | Content |
|---|---|
| `product`, `price`, `services` | Item name, base price, service charge |
| Weight columns (one per person) | Integer weights: `1` = equal share, `0` = excluded, custom for % or fixed splits |
| AMD amount columns (one per person) | Each person's exact share in AMD (decimal, sums precisely to net price) |

Footer rows:
- Per-person AMD totals
- Grand total
- **If Revolut:** EUR paid, rate, AMD verification total, weekend fee, EUR per person

---

## Temporary participants

Both `split_basket.py` and `manual_split.py` (and `run.py`) ask at the start:

```
Temporary participants? (names comma-separated, or Enter to skip):
```

These are added for the current run only and not saved to `.env`.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `No JWT found` | Run `auth_yc.py` |
| `Unauthorized (401)` | JWT expired — run `auth_yc.py` again |
| `Order cache not found` | Run `fetch_order.py` first |
| `Percentages sum to X%` | Your % values must add up to exactly 100% |
| `Fixed amounts sum to X AMD, but item is Y AMD` | Amounts must match the item's net price exactly |
| Small AMD discrepancy (1–2 AMD) | Normal rounding — not an error |

---

## File layout

```
.env                          # credentials and config (gitignored)
tools/
  auth_yc.py                  # phone OTP login → saves JWT
  fetch_order.py              # fetch latest YC order → .tmp/order_<id>.json
  split_basket.py             # interactive item splitter → .tmp/split_<id>.json
  manual_split.py             # manual expense splitter → .tmp/split_<slug>.json
  generate_csv.py             # CSV report → .tmp/report_<id>.csv
  run.py                      # full pipeline with interactive menu
  yc_client.py                # Yerevan City API client (auth, orders)
workflows/
  split_order.md              # detailed SOP with edge cases and API quirks
.tmp/                         # generated files (gitignored, safe to delete)
```
