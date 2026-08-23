# Workflow: Split Yerevan City Order

**Objective:** Fetch the latest YC order, split it item-by-item among participants, and produce a formatted Google Sheets report.

---

## Prerequisites

**One-time setup (do once, not every run):**

1. **Python venv** — already created at `.venv/`. Always run tools with:
   ```
   .venv/bin/python tools/<script>.py
   ```

2. **Google ADC** — authenticate your personal Gmail once:
   ```
   gcloud auth application-default login
   ```
   This is separate from `gcloud auth login`. Both are needed.

3. **YC auth** — first run only, or when JWT expires:
   ```
   .venv/bin/python tools/auth_yc.py
   ```
   You'll receive an SMS OTP. Enter it. JWT is saved to `.env`.

4. **GOOGLE_SHEET_ID** — left empty on first run. `generate_report.py` creates the spreadsheet automatically and writes the ID to `.env`.

---

## Per-Run Workflow

### Step 1 — Fetch latest order

```bash
.venv/bin/python tools/fetch_order.py
```

**What it does:**
- Reads `YC_JWT` from `.env`
- Calls `GET /Order/UserAllOrdersPaged` (page 1, count 1)
- Fetches full detail via `GET /Order/GetOfflineOrderById`
- Caches result to `data/order_{order_id}.json`

**If it fails with "Unauthorized":** JWT expired — run `auth_yc.py` first.

**If you want to re-fetch** (already cached): add `--refresh`:
```bash
.venv/bin/python tools/fetch_order.py --refresh
```

**Output:** order ID and summary printed to terminal. Note the order ID for next step.

---

### Step 2 — Split the basket interactively

```bash
.venv/bin/python tools/split_basket.py <order_id>
```

Example:
```bash
.venv/bin/python tools/split_basket.py KM0029977560
```

**What it does:**
1. Asks: `Temporary participants? (names comma-separated, or Enter to skip)`
   - Default participants are: **Me, Mahdi, Amir** (from `DEFAULT_PARTICIPANTS` in `.env`)
   - Temp participants are added for this run only
2. For each active (non-canceled) item, shows:
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
3. After all items: allocates fees (delivery, service, tip) proportionally by each person's item total
4. Prints a full summary
5. Asks about **payment method**:
   - **Cash** → no further steps, saves and exits
   - **Revolut** → asks for:
     - EUR → AMD conversion rate (e.g. `411.50`)
     - Total EUR paid (as shown in Revolut)
     - Whether the purchase was made on a **weekend** (Sat/Sun) — if yes, a 1% Revolut exchange markup is added on top of the paid EUR amount
   - Prints per-person EUR shares and saves to split file
6. Saves `data/split_{order_id}.json`

**Assignment input formats:**

| Input | Meaning |
|---|---|
| `Enter` or `all` | Equal split among **all** active participants |
| `me` | 100% to Me |
| `me,mahdi` | Equal split between Me and Mahdi only |
| `me:60%,mahdi:40%` | Percentage split (must sum to 100%) |
| `me:1200,mahdi:600` | Fixed AMD (must sum to item net price) |

**Name matching:** Case-insensitive and prefix-aware (`m` → `Me` if unambiguous).

**Fee allocation logic:** Each person's share of delivery/service/tip is proportional to their item total. Uses largest-remainder method — guaranteed to sum exactly to the total fee. Participants with zero item total get zero fees.

---

### Step 3 — Generate Tricount CSV report

```bash
.venv/bin/python tools/generate_csv.py <order_id>
```

**What it does:**
- Reads `data/split_{order_id}.json`
- Writes `data/report_{order_id}.csv` in the Tricount tracking format:

| Column group | Columns |
|---|---|
| Fixed | product, price, services (0 for YC) |
| Weights | One integer per participant — equal share = 1, sole owner = N (number of participants), excluded = 0 |
| AMD amounts | Each participant's actual share in AMD |

Footer rows:
- Per-person AMD totals
- Grand total (centre of AMD block)
- **If Revolut:** EUR paid, rate, AMD verification total, weekend fee (0 or 1% of EUR paid), EUR per person

**Open the file:**
```bash
open data/report_<order_id>.csv
```

**If the file already exists:** It is overwritten (idempotent — safe to re-run).

---

## Full Run (copy-paste)

```bash
cd /Users/mmpdev/develop/CA-YerevanCity

# If JWT is expired first:
# .venv/bin/python tools/auth_yc.py

.venv/bin/python tools/fetch_order.py
.venv/bin/python tools/split_basket.py <order_id_from_above>
.venv/bin/python tools/generate_csv.py <order_id_from_above>
open data/report_<order_id_from_above>.csv
```

---

## Handling Errors

| Error | Fix |
|---|---|
| `No JWT found` | Run `auth_yc.py` |
| `Unauthorized (401)` | JWT expired — run `auth_yc.py` |
| `Google ADC not found` | Run `gcloud auth application-default login` |
| `Spreadsheet not found` | Clear `GOOGLE_SHEET_ID` in `.env` — a new one will be created |
| `Percentages sum to X%, must be 100%` | Recheck your % values |
| `Fixed amounts sum to X AMD, but item is Y AMD` | Amounts must match the net price exactly |
| `Discrepancy of N AMD` shown in summary | Check for items skipped or rounding edge cases — small rounding differences (1–2 AMD) are normal |

---

## Data Files

| File | Purpose | Regenerate? |
|---|---|---|
| `.env` | Config, credentials | Never overwrite manually except via `auth_yc.py` |
| `data/order_{id}.json` | Raw order cache | Yes — `fetch_order.py --refresh` |
| `data/split_{id}.json` | **Your actual split record** | **No** — re-running `split_basket.py` produces a *new* split, not a recovery of a lost one. Back this up; never delete `data/`. |
| `.venv/` | Python packages | `python3 -m venv .venv && .venv/bin/pip install ...` |

---

## Maintenance Notes

- **JWT lifespan:** Unknown TTL — expect to re-auth every few weeks. `auth_yc.py` handles it in under 30 seconds.
- **Device ID:** Generated once, persisted in `.env`. Never change it — it's tied to your YC session identity.
- **API quirks (from TMA-YC):**
  - `osType` must be `2` (Postman collection had wrong value `3`)
  - `createdOn` in `GetOfflineOrderById` must be `YYYY-MM-DD` date only; full ISO datetime returns a 500 error
  - `createdOn` must be the order's **local (Armenia, UTC+4)** date, NOT the raw UTC date from `createDate`. The endpoint joins line items by local calendar date, so an order placed 20:00–23:59 UTC (00:00–03:59 local) is stored under the *next* day and returns `orderItems: []` (with a still-correct `totalPrice`) if looked up by its UTC date. `fetch_order._parse_date` converts UTC→UTC+4 before slicing the date. Symptom if this regresses: "0 active items" but correct total. (Armenia is a fixed UTC+4, no DST.)
  - `offlineOrderId` ("KM...") is the key for `GetOfflineOrderById`, not `id`
  - Prices from the API are floats — all stored and computed as integer AMD (whole drams)
  - For offline/pickup orders, `price` in `orderItems` is the **line total** (not per-unit); `totalPrice` is always 0 for these orders. Per-unit price is back-calculated as `price / quantity`.
- **Rounding:** Largest-remainder method is used everywhere. Sum of all splits always equals the item's net price exactly.
- **Participants:** `DEFAULT_PARTICIPANTS` in `.env` controls the base list. Temporary participants are added per-run via the CLI prompt and are not persisted.
