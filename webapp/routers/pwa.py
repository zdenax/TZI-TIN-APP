"""PWA a statika (WASM, manifest, service worker), webhook a hlavní stránka."""
import secrets
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, FileResponse
import tzi_trener
from ..config import WEBHOOK_SECRET
from ..git_sync import git_pull
from ..sessions import get_current_user, require_user
from ..csrf import CSRF_COOKIE_NAME, generate_csrf_token, ensure_csrf_token, safe_compare

router = APIRouter()


# --- PWA & WASM Endpoints ---
@router.get("/quiz.wasm")
def get_quiz_wasm():
    return FileResponse(tzi_trener.UI_DIR / "quiz.wasm", media_type="application/wasm", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@router.get("/manifest.webmanifest")
def get_manifest():
    return FileResponse(tzi_trener.UI_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@router.get("/sw.js")
def get_sw():
    return FileResponse(tzi_trener.UI_DIR / "sw.js", media_type="application/javascript", headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache, no-store, must-revalidate"})


@router.get("/icon.svg")
def get_icon():
    return FileResponse(tzi_trener.UI_DIR / "icon.svg", media_type="image/svg+xml")


@router.get("/favicon.ico")
def get_favicon():
    return FileResponse(tzi_trener.UI_DIR / "icon.svg", media_type="image/svg+xml")


_NO_STORE_HEADERS = {"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"}


def _auth_page(request: Request, filename: str):
    if not get_current_user(request):
        return RedirectResponse(url="/login")
    path = tzi_trener.UI_DIR / filename
    if not path.is_file():
        return PlainTextResponse("Chybí soubor šablony UI.", status_code=500)
    resp = FileResponse(path, media_type="text/html; charset=utf-8", headers=_NO_STORE_HEADERS)
    ensure_csrf_token(request, resp)
    return resp


@router.get("/fmt.js")
def get_fmt_js(user: Dict[str, Any] = Depends(require_user)):
    return FileResponse(tzi_trener.UI_DIR / "fmt.js", media_type="text/javascript; charset=utf-8", headers=_NO_STORE_HEADERS)


@router.get("/automat-core.js")
def get_automat_core_js(user: Dict[str, Any] = Depends(require_user)):
    return FileResponse(tzi_trener.UI_DIR / "automat-core.js", media_type="text/javascript; charset=utf-8", headers=_NO_STORE_HEADERS)


@router.get("/automat-delta.jpg")
def get_automat_delta_jpg(user: Dict[str, Any] = Depends(require_user)):
    return FileResponse(tzi_trener.UI_DIR / "automat-delta.jpg", media_type="image/jpeg", headers=_NO_STORE_HEADERS)


@router.get("/automat")
def get_automat(request: Request):
    return _auth_page(request, "automat.html")


@router.get("/teorie")
def get_teorie(request: Request):
    return _auth_page(request, "glosar.html")


@router.get("/glosar")
def get_glosar(request: Request):
    if not get_current_user(request):
        return RedirectResponse(url="/login")
    return RedirectResponse(url="/teorie", status_code=302)


@router.post("/webhook")
def post_webhook(request: Request, secret: str = ""):
    header_secret = request.headers.get("X-Webhook-Secret") or secret
    if not WEBHOOK_SECRET or not safe_compare(header_secret, WEBHOOK_SECRET):
        raise HTTPException(status_code=403, detail="Forbidden")
    out = git_pull()
    return PlainTextResponse(f"OK: {out}")


# --- Main Frontend View ---
@router.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")

    try:
        content = tzi_trener.load_ui("novy")
    except OSError:
        return PlainTextResponse("Chybí soubor šablony UI.", status_code=500)

    resp = HTMLResponse(content)
    ensure_csrf_token(request, resp)
    return resp
