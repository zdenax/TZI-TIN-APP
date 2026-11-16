from fastapi.staticfiles import StaticFiles
import tzi_trener
"""Skládá FastAPI aplikaci: inicializace DB, cache otázek, auto-sync bank a připojení routerů."""
import threading
import time

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

import db
from . import questions
from .config import HASHED_PASSWORD
from .git_sync import sync_worker
from .sessions import get_current_user
from .routers import account, admin, auth, competitive, pwa, study

# --- Initialize Database ---
db.init_db()
if HASHED_PASSWORD:
    db.ensure_admin_exists(HASHED_PASSWORD)

# Cache otázek pro anti-spoofing ověřování odpovědí
questions.refresh_questions()

# Pravidelný auto-sync bank otázek z upstreamu
threading.Thread(target=sync_worker, daemon=True).start()

# --- FastAPI Application ---
app = FastAPI(title="TZI Trenér", docs_url=None, redoc_url=None)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    if request.url.path in ("/automat", "/teorie", "/glosar"):
        csp = (
            "default-src 'none'; "
            "script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "img-src 'self' data: blob:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none'"
        )
    else:
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "img-src 'self' data: blob:; "
            "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.gstatic.com data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none'"
        )
    if request.url.scheme == "https":
        csp += "; upgrade-insecure-requests"
    response.headers["Content-Security-Policy"] = csp
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return response


@app.middleware("http")
async def audit_communication_middleware(request: Request, call_next):
    path = request.url.path
    # Přeskočit statické soubory a PWA ikony, ať nezahlcují DB
    if path.startswith("/static") or path in ("/sw.js", "/manifest.webmanifest", "/icon.svg", "/favicon.ico"):
        return await call_next(request)

    # Přeskočit i samotné logování chyb aby nedošlo k rekurzi
    if path == "/api/client-error":
        return await call_next(request)

    t0 = time.time()
    user_id = None
    try:
        u = get_current_user(request)
        if u:
            user_id = u.get("user_id")
    except Exception:
        pass

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = int((time.time() - t0) * 1000)
        ip = request.client.host if request.client else "unknown"
        db.log_error(
            level="ERROR",
            message=f"{request.method} {path} -> 500 Exception: {str(exc)} [{duration_ms}ms, ip={ip}]",
            endpoint=path,
            user_id=user_id,
            stack_trace=str(exc)
        )
        raise exc

    duration_ms = int((time.time() - t0) * 1000)
    status_code = response.status_code
    ip = request.client.host if request.client else "unknown"

    # Logovat WARNING pro 4xx odpovědi (neúspěšné pokusy, rate limity, odmítnutí)
    if 400 <= status_code < 500:
        db.log_error(
            level="WARNING",
            message=f"{request.method} {path} -> {status_code} [{duration_ms}ms, ip={ip}]",
            endpoint=path,
            user_id=user_id
        )
    # Logovat INFO pro API a formulářové komunikace (POST, PUT, DELETE nebo /api/*)
    elif path.startswith("/api/") or request.method in ("POST", "PUT", "DELETE"):
        db.log_error(
            level="INFO",
            message=f"{request.method} {path} -> {status_code} [{duration_ms}ms, ip={ip}]",
            endpoint=path,
            user_id=user_id
        )

    return response

# Statické soubory pro modularizované UI (CSS, JS)
app.mount("/static", StaticFiles(directory=tzi_trener.UI_DIR), name="static")

for _router in (auth.router, admin.router, study.router, account.router, competitive.router, pwa.router):
    app.include_router(_router)
