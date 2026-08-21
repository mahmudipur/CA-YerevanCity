#!/usr/bin/env bash
# Build the frontend and start the web app locally, with an ngrok tunnel so
# it's reachable even when you're away from this machine.
#
#   ./web/run.sh              # local + ngrok tunnel (default), port 8420
#   NGROK=0 ./web/run.sh      # local only, no tunnel
#   PORT=9000 ./web/run.sh    # use a different port
#
# Local: http://localhost:$PORT (or http://<this-machine's-LAN-IP>:$PORT on the same WiFi)
# Remote: the ngrok URL printed below, reachable from anywhere.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d .venv ]; then
  echo "No .venv found. Create one first: python3 -m venv .venv"
  exit 1
fi

PORT="${PORT:-8420}"

if lsof -iTCP:"$PORT" -sTCP:LISTEN -P >/dev/null 2>&1; then
  echo "==> Port $PORT is already in use by another process:"
  lsof -iTCP:"$PORT" -sTCP:LISTEN -P | tail -n +2
  echo "==> Pick a free one with: PORT=<other-port> ./web/run.sh"
  exit 1
fi

echo "==> Installing backend deps"
.venv/bin/pip install -q -r web/backend/requirements-web.txt

echo "==> Building frontend"
cd web/frontend
if [ ! -d node_modules ]; then
  npm install
fi
npm run build
cd "$ROOT_DIR"

USE_NGROK="${NGROK:-1}"
NGROK_PID=""
SERVER_PID=""

cleanup() {
  [ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
  [ -n "$NGROK_PID" ] && kill "$NGROK_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Starting server on http://0.0.0.0:$PORT"
PORT="$PORT" .venv/bin/python web/backend/run_web.py &
SERVER_PID=$!

# Give uvicorn a moment to actually bind before trusting it's up.
sleep 1
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "==> Server failed to start — see output above."
  exit 1
fi

if [ "$USE_NGROK" = "1" ]; then
  if ! command -v ngrok >/dev/null 2>&1; then
    echo "==> ngrok not found (brew install ngrok) — continuing local-only."
  else
    echo "==> Starting ngrok tunnel"
    ngrok http "$PORT" --log stdout > /tmp/yc-split-ngrok.log 2>&1 &
    NGROK_PID=$!

    PUBLIC_URL=""
    for _ in $(seq 1 20); do
      sleep 0.5
      PUBLIC_URL="$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null \
        | .venv/bin/python -c 'import json,sys
try:
    data = json.load(sys.stdin)
    urls = [t["public_url"] for t in data.get("tunnels", []) if t["public_url"].startswith("https")]
    print(urls[0] if urls else "")
except Exception:
    print("")' 2>/dev/null)"
      [ -n "$PUBLIC_URL" ] && break
    done

    if [ -n "$PUBLIC_URL" ]; then
      echo ""
      echo "==> Public URL (reachable from anywhere): $PUBLIC_URL"
      echo "==> Local URL: http://localhost:$PORT"
      echo ""
    else
      echo "==> ngrok didn't come up in time — check /tmp/yc-split-ngrok.log"
    fi
  fi
fi

wait "$SERVER_PID"
