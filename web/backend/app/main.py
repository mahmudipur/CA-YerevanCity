from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from . import sys_path  # noqa: F401  (side effect: primes sys.path for tools/)
from .config import FRONTEND_DIST
from .db import init_db
from .rate_limit import limiter
from .routers import auth, export, history, orders, password_auth, payment, receipt, sessions, telegram_auth


@asynccontextmanager
async def _lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Yerevan City Split — Web", lifespan=_lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# The SPA is normally served same-origin from this same process (no CORS
# needed at all in that case), but this app is also commonly run with the
# Vite dev server on a different port, or exposed only partially through an
# ngrok tunnel — both of which the browser treats as cross-origin, and a
# POST with a JSON body then requires a working CORS preflight (OPTIONS)
# response or the browser silently blocks the real request before it's ever
# sent. Scoped to localhost (any port, for the dev-server workflow) and
# ngrok's own tunnel domains — not a blanket wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https://[a-z0-9-]+\.ngrok(-free)?\.(app|io)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(telegram_auth.router)
app.include_router(telegram_auth.me_router)
app.include_router(password_auth.router)
app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(sessions.router)
app.include_router(payment.router)
app.include_router(export.router)
app.include_router(history.router)
app.include_router(receipt.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        # Every /api/ response is per-session/account state (auth status,
        # orders, splits) — never let a browser or intermediary serve a
        # cached copy across a login/logout, or across two different users
        # of the same browser profile.
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Telegram's Login Widget loads a script from telegram.org and opens an
    # oauth.telegram.org frame — CSP must allow exactly those, nothing wider.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' https://telegram.org; "
        "frame-src https://oauth.telegram.org; "
        "connect-src 'self'; "
        "img-src 'self' https://t.me data:; "
        "style-src 'self' 'unsafe-inline'"
    )
    return response


@app.get("/api/health")
def health():
    return {"ok": True}


# Serve the built React SPA (npm run build -> web/frontend/dist), if present.
# In dev, the Vite dev server runs separately and proxies /api here instead.
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="spa-assets")

    @app.get("/{full_path:path}")
    async def spa_catch_all(full_path: str):
        """Serve index.html for any non-API route so client-side routing
        (React Router) works on hard refresh / deep links."""
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
