"""Studijní API: profil, otázky, postup a synchronizace offline fronty."""
import json
import re
import time
from collections import defaultdict
from typing import Dict, Any, List
from fastapi import APIRouter, Request, Response, HTTPException, Depends
import db
import scoring
import tzi_trener
from .. import questions
from ..questions import verify_answer
from ..sessions import require_user
from ..csrf import ensure_csrf_token, validate_csrf

router = APIRouter()


# --- API Endpoints ---
@router.get("/api/me")
def api_me(request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)):
    csrf_tok = ensure_csrf_token(request, response)
    if user.get("role") == "trial" or user.get("user_id") == 0:
        return {
            "user_id": 0,
            "username": "Host (Trial)",
            "role": "trial",
            "theme": "catppuccin",
            "csrf_token": csrf_tok,
            "points": 0,
            "streak": 0,
            "best_streak": 0,
            "daily_streak": 0,
            "best_daily_streak": 0,
            "daily_goal": scoring.DAILY_MIN_GOAL,
            "questions_today": 0,
            "daily_goal_met": False,
            "rank": "-",
            "total_users": "-"
        }
    user_db = db.get_user_by_id(user["user_id"])
    stats = scoring.get_user_leaderboard_position(user["user_id"])
    return {
        "user_id": user["user_id"],
        "username": user_db["username"] if user_db else user["username"],
        "role": user.get("role", "student"),
        "theme": user_db.get("theme", "games") if user_db else "games",
        "csrf_token": csrf_tok,
        "points": stats["points"],
        "streak": stats["current_streak"],
        "best_streak": stats["best_streak"],
        "daily_streak": stats["daily_streak"],
        "best_daily_streak": stats["best_daily_streak"],
        "daily_goal": stats["daily_goal"],
        "questions_today": stats["questions_today"],
        "daily_goal_met": stats["daily_goal_met"],
        "rank": stats["rank"],
        "total_users": stats["total"]
    }


@router.get("/api/daily-progress")
def api_daily_progress(user: Dict[str, Any] = Depends(require_user)):
    if user.get("role") == "trial" or user.get("user_id") == 0:
        return {
            "date": "",
            "questions_answered": 0,
            "questions_correct": 0,
            "daily_goal": scoring.DAILY_MIN_GOAL,
            "goal_met": False,
            "daily_streak": 0,
            "best_daily_streak": 0,
            "last_goal_date": None,
            "history": []
        }
    return scoring.get_daily_progress(user["user_id"])


@router.get("/api/sources")
def api_sources(user: Dict[str, Any] = Depends(require_user)):
    srcs = tzi_trener.list_sources()
    real = [s for s in srcs if s["id"] != tzi_trener.ALL]
    default = real[-1]["id"] if real else ""
    return {"sources": srcs, "default": default}


@router.get("/api/questions")
def api_questions(source: str = "", user: Dict[str, Any] = Depends(require_user)):
    try:
        return tzi_trener.load_questions(source)
    except (KeyError, OSError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/recall")
def api_recall(user: Dict[str, Any] = Depends(require_user)):
    try:
        return tzi_trener.load_recall()
    except (KeyError, OSError, ValueError) as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/teorie")
@router.get("/api/glosar")
def api_glosar(response: Response, source: str = "", user: Dict[str, Any] = Depends(require_user)):
    if not source or len(source) > 64 or not re.fullmatch(r"[A-Za-z0-9_-]+", source):
        raise HTTPException(status_code=400, detail="Neplatný parametr source")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    try:
        return tzi_trener.load_glosar(source)
    except (KeyError, OSError, ValueError):
        raise HTTPException(status_code=404, detail="Zdroj nebyl nalezen")


@router.get("/api/progress")
def api_get_progress(source: str = "", user: Dict[str, Any] = Depends(require_user)):
    user_id = user["user_id"]
    if user.get("role") == "trial" or user_id == 0:
        return {"seen": {}, "session": None}

    conn = db.get_db()

    # 1. Získat celkový agregovaný přehled 'seen' ze všech přednášek
    all_seen = {}
    rows = conn.execute("SELECT seen_json FROM user_progress WHERE user_id = ?", (user_id,)).fetchall()
    for r in rows:
        try:
            d = json.loads(r["seen_json"])
            all_seen.update(d)
        except Exception:
            pass

    # 2. Získat session pro konkrétní zvolený zdroj
    active_session = None
    if source:
        row = conn.execute(
            "SELECT session_json FROM user_progress WHERE user_id = ? AND source = ?",
            (user_id, source)
        ).fetchone()
        if row and row["session_json"]:
            try:
                active_session = json.loads(row["session_json"])
            except Exception:
                pass

    return {"seen": all_seen, "session": active_session}


# --- Rate limiting pro /api/progress (max 60 požadavků za 60 s na uživatele / IP) ---
_progress_rate_limits: dict[str, List[float]] = defaultdict(list)
PROGRESS_MAX_REQUESTS = 60
PROGRESS_WINDOW = 60  # sekund


def _check_progress_rate_limit(key: str) -> bool:
    """Vrací True pokud je požadavek povolen, False pokud překročil limit."""
    now = time.time()
    window_start = now - PROGRESS_WINDOW
    timestamps = [t for t in _progress_rate_limits[key] if t > window_start]
    if len(timestamps) >= PROGRESS_MAX_REQUESTS:
        _progress_rate_limits[key] = timestamps
        return False
    timestamps.append(now)
    _progress_rate_limits[key] = timestamps
    return True


def reset_progress_rate_limits():
    """Pomocná funkce pro testy k resetování stavu progress rate limiteru."""
    _progress_rate_limits.clear()


@router.post("/api/progress")
async def api_post_progress(request: Request, response: Response, source: str = "", user: Dict[str, Any] = Depends(require_user)):
    await validate_csrf(request, response, rotate=False)
    user_id = user["user_id"]
    ip = request.client.host if request.client else "unknown"
    rate_key = f"u_{user_id}" if user_id else f"ip_{ip}"
    if not _check_progress_rate_limit(rate_key):
        raise HTTPException(status_code=429, detail="Příliš mnoho požadavků na záznam postupu. Počkejte chvíli.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Neplatný JSON")

    # Pokud jde o Trial mód, nic neukládáme do databáze a nepočítáme globální skóre
    if user.get("role") == "trial" or user_id == 0:
        return {"ok": True, "score": None}

    seen = payload.get("seen", {})
    session = payload.get("session")
    latest_answer = payload.get("latest")

    # Pokud klient poslal explicitní informaci o poslední zodpovězené otázce
    score_result = None
    if latest_answer is not None:
        if not isinstance(latest_answer, dict) or "id" not in latest_answer:
            raise HTTPException(status_code=400, detail="Neplatný formát odpovědi (chybí id)")

        q_id = str(latest_answer["id"])
        if not questions.ALL_QUESTIONS:
            questions.refresh_questions()
        q = questions.ALL_QUESTIONS.get(q_id)
        if not q:
            raise HTTPException(status_code=400, detail=f"Neznámá otázka: {q_id}")

        # Anti-spoofing: striktně vyžadovat userKeys nebo user_answer, zakázat isCorrect fallback
        u_ans = None
        if "userKeys" in latest_answer and latest_answer["userKeys"] is not None:
            u_ans = latest_answer["userKeys"]
        elif "user_answer" in latest_answer and latest_answer["user_answer"] is not None:
            u_ans = latest_answer["user_answer"]
        else:
            raise HTTPException(status_code=400, detail="Chybí userKeys nebo user_answer")

        is_correct = verify_answer(q, u_ans)
        score_result = scoring.record_question_answer(user_id, q_id, is_correct)

    # Uložit stav do user_progress
    conn = db.get_db()
    with conn:
        conn.execute(
            """
            INSERT INTO user_progress (user_id, source, seen_json, session_json, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, source) DO UPDATE SET
                seen_json = excluded.seen_json,
                session_json = excluded.session_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, source or "_default", json.dumps(seen, ensure_ascii=False), json.dumps(session, ensure_ascii=False) if session else None)
        )

    return {"ok": True, "score": score_result}


# --- Rate limiting pro /api/sync (max 10 požadavků za 60 s na uživatele / IP) ---
_sync_rate_limits: dict[str, List[float]] = defaultdict(list)
SYNC_MAX_REQUESTS = 10
SYNC_WINDOW = 60  # sekund


def _check_sync_rate_limit(key: str) -> bool:
    """Vrací True pokud je sync povolen, False pokud je překročen limit."""
    now = time.time()
    window_start = now - SYNC_WINDOW
    timestamps = [t for t in _sync_rate_limits[key] if t > window_start]
    if len(timestamps) >= SYNC_MAX_REQUESTS:
        _sync_rate_limits[key] = timestamps
        return False
    timestamps.append(now)
    _sync_rate_limits[key] = timestamps
    return True


def reset_sync_rate_limits():
    """Pomocná funkce pro testy k resetování stavu sync rate limiteru."""
    _sync_rate_limits.clear()


@router.post("/api/sync")
async def api_sync(request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)):
    """Offline synchronizace: dávkové bezpečné zpracování odpovědí vyřešených offline s anti-spoofing kontrolou."""
    await validate_csrf(request, response, rotate=False)
    user_id = user["user_id"]
    ip = request.client.host if request.client else "unknown"
    rate_key = f"u:{user_id}_ip:{ip}"
    if not _check_sync_rate_limit(rate_key):
        raise HTTPException(status_code=429, detail="Příliš mnoho synchronizačních požadavků. Počkejte chvíli.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Neplatný JSON")

    if user.get("role") == "trial" or user_id == 0:
        return {"ok": True, "synced_count": 0, "points_awarded": 0, "leaderboard": None}

    answers = payload.get("answers", [])
    if not isinstance(answers, list):
        raise HTTPException(status_code=400, detail="answers musí být list")

    # Anti-spoofing limit na velikost jedné dávky
    if len(answers) > 100:
        answers = answers[:100]

    seen = payload.get("seen", {})
    source = payload.get("source", "_default")

    total_points_gained = 0
    synced_count = 0
    seen_ids = set()

    for item in answers:
        if not isinstance(item, dict):
            continue
        q_id = str(item.get("id", ""))
        if not q_id or q_id in seen_ids:
            continue
        seen_ids.add(q_id)

        q = questions.ALL_QUESTIONS.get(q_id)
        if not q:
            continue

        u_ans = item.get("user_answer") or item.get("userKeys")
        if u_ans is None:
            continue

        # Anti-spoofing: přísná validace serverem
        is_correct = verify_answer(q, u_ans)
        res = scoring.record_question_answer(user_id, q_id, is_correct)
        if res and res.get("points_awarded", 0) > 0:
            total_points_gained += res["points_awarded"]
        synced_count += 1

    if seen:
        conn = db.get_db()
        with conn:
            conn.execute(
                """
                INSERT INTO user_progress (user_id, source, seen_json, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, source) DO UPDATE SET
                    seen_json = excluded.seen_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, source, json.dumps(seen, ensure_ascii=False))
            )

    pos = scoring.get_user_leaderboard_position(user_id)
    return {
        "ok": True,
        "synced_count": synced_count,
        "points_awarded": total_points_gained,
        "leaderboard": pos
    }


# --- Rate limiting pro /api/client-error (10 požadavků za 60 s na IP) ---
_client_error_rate_limits: dict[str, List[float]] = defaultdict(list)
CLIENT_ERROR_MAX_REQUESTS = 10
CLIENT_ERROR_WINDOW = 60  # sekund


def _check_client_error_rate_limit(ip: str) -> bool:
    """Vrací True pokud je požadavek povolen, False pokud IP překročila limit."""
    now = time.time()
    window_start = now - CLIENT_ERROR_WINDOW
    timestamps = [t for t in _client_error_rate_limits[ip] if t > window_start]
    if len(timestamps) >= CLIENT_ERROR_MAX_REQUESTS:
        _client_error_rate_limits[ip] = timestamps
        return False
    timestamps.append(now)
    _client_error_rate_limits[ip] = timestamps
    return True


def reset_client_error_rate_limits():
    """Pomocná funkce pro testy k resetování stavu rate limiteru."""
    _client_error_rate_limits.clear()


@router.post("/api/client-error")
async def api_client_error(request: Request):
    ip = request.client.host if request.client else "unknown"
    if not _check_client_error_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Příliš mnoho chybových hlášení. Rate limit překročen.")
    try:
        body = await request.json()
    except Exception:
        body = {}
    msg = str(body.get("message", "Unknown error"))[:500]
    ep = str(body.get("file", ""))[:200]
    stack = str(body.get("stack", ""))[:2000]
    db.log_error("UI_ERROR", msg, endpoint=ep, stack_trace=stack)
    return {"ok": True}

