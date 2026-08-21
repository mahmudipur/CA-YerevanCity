from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import sys_path  # noqa: F401  (side effect: primes sys.path for tools/)
from .config import FRONTEND_DIST
from .routers import auth, export, history, orders, payment, receipt, sessions

app = FastAPI(title="Yerevan City Split — Web")

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
