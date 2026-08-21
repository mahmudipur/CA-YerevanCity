#!/usr/bin/env python3
"""
Local entrypoint for the web app.

Build the frontend once (from web/frontend): npm install && npm run build
Then run:
  .venv/bin/python web/backend/run_web.py

Serves the API + built SPA from a single process/port, reachable over LAN
via this machine's IP (e.g. http://192.168.x.x:8420).

Port defaults to 8420 (not 8000 — commonly already taken by Docker Desktop
and other local dev tooling). Override with the PORT env var.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8420"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
