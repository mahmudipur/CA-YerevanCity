# Web App (local)

The terminal CLI (`tools/run.py` and friends) still works exactly as before and
is unaffected by any of this. This is an additive web UI over the same
calculation logic, for when you'd rather use your phone/browser than a
terminal.

## What it is

- Backend: FastAPI (`web/backend/`), imports `tools/split_math.py`,
  `tools/split_basket.py`, `tools/fetch_order.py`, `tools/manual_split.py`,
  `tools/generate_csv.py`, `tools/yc_client.py` **unchanged** — no calculation
  logic is duplicated or re-implemented.
- Frontend: React + TypeScript + Vite + Tailwind + Framer Motion SPA
  (`web/frontend/`), mirroring the terminal's roster → per-item assignment →
  review/edit → summary → payment flow, mobile-first and installable to a
  phone home screen.
- Both the CLI and the web app read/write the same `.env` and `.tmp/` files,
  so either can pick up where the other left off.

## Running it

```bash
./web/run.sh              # local + ngrok tunnel (default), port 8420
NGROK=0 ./web/run.sh      # local only, no tunnel
PORT=9000 ./web/run.sh    # use a different port
```

This installs the backend's extra dependencies (`web/backend/requirements-web.txt`,
kept separate from the root `requirements.txt` so a terminal-only install
never needs them), builds the frontend once, and starts the server on port
**8420** by default — deliberately not 8000, since that's commonly already
taken by Docker Desktop or other local dev tooling. `run.sh` checks the port
is actually free before doing anything and tells you which process is
holding it (with a `PORT=<other> ./web/run.sh` suggestion) if not.

Open `http://localhost:8420` on this machine, or `http://<LAN-IP>:8420` from
your phone on the same WiFi network.

By default it also starts an `ngrok http $PORT` tunnel (requires `ngrok` —
`brew install ngrok` — already authenticated via `ngrok config add-authtoken`)
and prints the public HTTPS URL it assigns, e.g.:

```
==> Public URL (reachable from anywhere): https://xxxx-xx-xx-xx-xx.ngrok-free.app
```

That URL works from any network — useful for opening a split from your phone
when you're not on the same WiFi as this machine. It changes every time you
restart `run.sh` (free ngrok tier doesn't reserve a fixed subdomain). Ctrl-C
stops both the server and the tunnel together.

**What "public" actually means here**: anyone with that URL can use the full
app — view/edit past splits, start new ones, trigger a Yerevan City sign-in
attempt (though completing it still requires the OTP sent to your phone).
There's no login of the app's own guarding those pages. The URL isn't
published anywhere and free-tier ngrok subdomains aren't practically
guessable, but treat the link itself as something not to share. Every
`split_id`/`order_id` used in a URL is validated against a strict
alphanumeric/`_`/`-` pattern before it's ever used to build a file path
(`validate_id()` in `persistence.py`), so a malicious id in a request can't
reach files outside `.tmp/`. Pass `NGROK=0` to skip the tunnel entirely and
stay LAN-only.

## Development (hot reload)

Run two processes:

```bash
# Terminal 1 — API with reload
.venv/bin/pip install -r web/backend/requirements-web.txt
.venv/bin/python -m uvicorn app.main:app --reload --port 8420 --app-dir web/backend

# Terminal 2 — Vite dev server (proxies /api to :8420)
cd web/frontend && npm install && npm run dev
```

Open the Vite dev server URL it prints (usually `http://localhost:5173`).

## Tests

```bash
# Existing CLI/calculation tests — must always keep passing unmodified
.venv/bin/python -m pytest tests/ -q

# Web backend tests, including a CLI-vs-web parity check against a fixture order
cd web/backend && ../../.venv/bin/python -m pytest tests/ -q
```

`web/backend/tests/test_parity.py` proves the web wizard produces the exact
same split JSON (aside from the timestamp) as assembling one directly from
the unchanged calculation functions, for the same scripted sequence of
per-item assignments. `test_payment_parity.py` pins the Revolut fee/EUR-split
math with golden values. `test_csv_export.py` confirms the CSV download
endpoint calls the real, unmodified `generate_csv.py` logic.

## Manual end-to-end check

1. Start the web app, complete one full split in the browser (any small
   manual expense is easiest), and note the split id it prints.
2. From the terminal, run `python tools/generate_csv.py <id>` against the
   same `.tmp/split_<id>.json` the web app wrote, and confirm it produces a
   normal CSV — proves the two paths share the exact same file format.

## One intentional edit to `tools/split_basket.py`

`collect_payment_info()` mixed its Revolut fee math with blocking `input()`
calls, so it couldn't be imported into the web backend as-is. A pure helper,
`compute_revolut_currency(rate, eur_paid, is_weekend, is_fair_usage, totals,
participants)`, was extracted with the exact same formula; `collect_payment_info()`
now calls it internally instead of inlining the math. The CLI's behavior and
output are unchanged — see `test_payment_parity.py` for the pinned values.
Every other file under `tools/` is untouched.

## Product pictures

`tools/fetch_order.py`'s `_build_order` now also captures each order item's
`photo` URL from the Yerevan City API (field `image` in the order JSON, `null`
if the API didn't return one). This is purely additive — no existing keys
changed, no test pinned the old shape. Manual-expense items have no photo
(there's no product catalog for those), so `image` is simply absent/`null`
there and the UI just doesn't render a thumbnail.

## Editing a past split

`History` → the pencil icon on any row re-opens that split as a new editable
session (`POST /api/history/{split_id}/edit`), pre-populated with its
participants, items, existing per-item assignments, and payment info, then
drops you on the Review screen. It reuses the exact same
assign/finish/payment/save endpoints as a fresh split — the only difference is
`save` writes back to the *same* `split_{id}.json` (same `order_id`/slug),
so editing overwrites in place instead of creating a duplicate file. For a
Yerevan City order this also reconstructs `order` from the cached
`order_{id}.json` so fee amounts and item photos are available while editing;
if that cache is missing, order-level fields are rebuilt from what's stored in
the split JSON itself (fees, totals, meta), though this only happens if the
order cache was deleted separately from the split.

## Known limitations (v1)

- Session state (the in-progress wizard) lives in memory only. Killing the
  backend mid-session loses that session's progress — the same as Ctrl-C
  aborting the terminal CLI mid-flow. The canonical `split_*.json` file is
  only written once you reach "Confirm & save".
- No authentication layer of its own — relies on the ngrok URL staying
  unshared, or on staying LAN-only (`NGROK=0`). See the "public URL" note
  above.
