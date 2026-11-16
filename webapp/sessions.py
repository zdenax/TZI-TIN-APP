"""Podepsané session tokeny s IP/UA bindigem a závislosti pro autorizaci (require_user, require_admin)."""
import hashlib
import secrets
import time
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from itsdangerous import BadSignature, SignatureExpired
from .config import SESSION_COOKIE, SESSION_MAX_AGE, serializer
from .csrf import safe_compare


# --- Session Helpers ---
def _client_fingerprint(request: Request) -> str:
    """Vygeneruje stabilní hash z IP + User-Agent pro bindování session."""
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")
    return hashlib.sha256(f"{ip}|{ua}".encode()).hexdigest()[:16]


def create_session_token(user: Dict[str, Any], request: Optional[Request] = None) -> str:
    payload = {
        "user_id": user["id"],
        "username": user["username"],
        "role": user.get("role", "student"),
        "theme": user.get("theme", "games"),
        "fp": _client_fingerprint(request) if request else "",
        "ts": int(time.time())
    }
    return serializer.dumps(payload)


def verify_session_token(
    token: Optional[str],
    request: Optional[Request] = None,
) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    # IP/UA binding — porovná fingerprint z tokenu s aktuálním klientem
    if request and data.get("fp"):
        current_fp = _client_fingerprint(request)
        if not safe_compare(str(data["fp"]), current_fp):
            return None
    return data


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    token = request.cookies.get(SESSION_COOKIE)
    return verify_session_token(token, request)


def require_user(request: Request) -> Dict[str, Any]:
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nejste přihlášeni")
    return user


def require_admin(request: Request) -> Dict[str, Any]:
    user = require_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Pouze pro administrátora")
    return user
