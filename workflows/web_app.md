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
- The CLI still reads/writes the shared root `.env` for its own single
  account. The web app is now **multi-tenant**: each visitor signs in
  (Telegram and/or username/password — see "Accounts & login") and gets
  their own isolated account (own Yerevan City phone/OTP link, own
  splits/orders). Accounts live in `data/app.db` (SQLite, YC secrets and
  passwords encrypted/hashed at rest); every split/order/report file
  (`data/split_*.json`, `data/order_*.json`, `data/report_*.csv`) — for
  both the CLI and the web app — lives in that same `data/` directory.
  **`data/` is not `.tmp/`** — it's deliberately outside that disposable
  directory (see root `CLAUDE.md`) so clearing `.tmp/` never loses an
  account or a single past split. Only genuinely re-fetchable/regenerable
  things (order caches, CSV exports) are safe to delete at all, and even
  those now live in `data/` too, not `.tmp/` — `.tmp/` currently holds
  nothing this app depends on.

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

**What "public" actually means here**: anyone with that URL now gets a real
account of their own — every page except the anonymous-auth ones
(`/login`, `/signup`, `/forgot-password`) requires a signed-in session
(`Depends(get_current_user)` on every router), and every session/split/order
lookup is scoped to the caller's account id, so one tenant can't read or
mutate another's data by guessing an id (see "Accounts & login"). Every
`split_id`/`order_id` used in a URL is still validated against a strict
alphanumeric/`_`/`-` pattern before it's ever used to build a file path
(`validate_id()` in `persistence.py`).

**Telegram is optional here, deliberately.** This app runs on a local
machine behind a free (rotating-URL) ngrok tunnel, and Telegram's Login
Widget is bound to one exact hostname via BotFather's `/setdomain` — it
will not work against a URL that changes every restart. Username/password
signup (always available, see "Accounts & login") is the primary way in
for this setup; Telegram becomes usable later if a fixed domain (a real
reverse proxy + DNS, or a paid static ngrok domain) is ever put in front of
`run.sh`'s uvicorn process. Pass `NGROK=0` to skip the tunnel entirely and
stay LAN-only either way.

## Accounts & login

Two independent, **linkable** ways into an account — the same underlying
`User` row can have either or both. Only `user.id` (an autoincrement
integer, not a Telegram id) is used to scope sessions/splits/order caches,
since a password-only account has no `telegram_id`.

- **Username/password** (`routers/password_auth.py`) — always available,
  no configuration needed. Signup returns a one-time recovery code the UI
  forces you to acknowledge saving (`Signup.tsx`); there's no email/SMS to
  fall back on, so that code — or `python web/backend/scripts/reset_password.py
  <username>`, run locally by whoever operates the app — is the only way
  back in if a password is forgotten. Passwords are hashed with Argon2id
  (`services/password_auth.py`).
- **Telegram Login Widget** (`services/telegram_auth.py`, HMAC-SHA256-
  verified, not OAuth/OIDC) — optional. The frontend fetches
  `GET /api/auth/telegram/config` and simply doesn't render the widget when
  `TELEGRAM_BOT_USERNAME` is unset, so leaving all three Telegram env vars
  blank is a fully supported, no-op configuration. Configure a bot via
  [@BotFather](https://t.me/BotFather) and set `TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_BOT_USERNAME`, `TELEGRAM_LOGIN_DOMAIN` in `.env` only once you
  have a fixed domain — see the ngrok caveat above.
- **Linking**: a password account can connect Telegram (and vice versa)
  from `/account` — `POST /api/auth/telegram/link` /
  `POST /api/auth/set-password` — rejecting the link if that Telegram id is
  already claimed by a different account.
- After signing in by either method, each user does a one-time "link my
  Yerevan City account" step (the same phone+OTP flow as before, now scoped
  to them — `/api/auth/send-code` etc. in `routers/auth.py`) before they can
  fetch orders or save splits.
- Also generate and set `APP_MASTER_KEY` (encrypts each user's YC
  phone/device-id/JWT at rest) and `APP_SESSION_SECRET` (signs the app's own
  session cookie) — commands for both are in `.env.example`.
- The pre-existing owner account (this repo's original single-tenant `.env`)
  is migrated once via `python web/backend/scripts/migrate_legacy_env.py
  --username <you>`, which also sets a real password so that account is
  immediately usable (not an inert placeholder) at a reserved id
  (`LEGACY_USER_ID = 0`) — see that script's docstring for the full
  rationale and a `--claim-legacy` option.
- `send-code`/`verify`, the Telegram callback/link, and signup/login/
  forgot-password are all rate-limited (`slowapi`) since several of them
  hit a real third-party API or are password-guessing surfaces.

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
   same `data/split_<id>.json` the web app wrote, and confirm it produces a
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

## Tricount receipt image

The CSV report has no on-screen equivalent, so the natural workaround —
open the CSV in a spreadsheet app and screenshot it to paste into Tricount
as a receipt — falls apart on a phone: the sheet doesn't fit one screen, so
a screenshot only captures whatever's currently visible.
`GET /api/sessions/{split_id}/image` (button on the Done screen and on each
History row) renders the exact same rows as `generate_csv.py` — same
column layout, same math, refactored into a shared `build_report_rows()` so
neither format duplicates the other's logic — as a single PNG
(`tools/generate_receipt_image.py`, Pillow) sized to fit every row. One
download, no scrolling, works identically on a phone or a laptop. On
mobile the frontend uses the Web Share API when available (`useShareOrDownload.ts`)
so tapping the button opens the native share sheet straight into Photos or
Tricount's own attachment picker, falling back to a normal download link
everywhere else.

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

- Session state (the in-progress wizard) lives in memory only, per-user. Killing
  the backend mid-session loses everyone's in-progress sessions — the same as
  Ctrl-C aborting the terminal CLI mid-flow. The canonical `split_*.json` file
  is only written once you reach "Confirm & save". This also means the
  deployment must stay single-process/single-worker; if that ever needs to
  change, move `session_store.py` into SQLite with a TTL-cleanup job instead.
- The pre-existing owner's cached order files under `data/order_*.json` (from
  before multi-tenancy) are not auto-migrated to the new per-user
  `order_<user_id>_<id>.json` naming — they'll simply be re-fetched from
  Yerevan City the first time they're needed under the new scheme. This is
  fine — unlike `split_*.json`, order caches are pure re-fetchable cache,
  never the only copy of anything.
- No allowlist/invite gating — anyone can self-register (via Telegram or
  username/password) today by design. `services/user_store.create_password_account()`
  / `get_or_create_telegram_user()` are the two choke points where a gate
  could be added later if that changes.
- No email/SMS capability at all (this runs on a local machine) — signup's
  optional email field is never verified or used for anything, and
  forgot-password relies entirely on the one-time recovery code (or the
  operator manually running `scripts/reset_password.py`).
