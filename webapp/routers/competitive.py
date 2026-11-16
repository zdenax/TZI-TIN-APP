"""Soutěžní režimy: King of the Hill, FFA, 1v1 duel a místnosti (lobby)."""
import json
from typing import Optional, Dict, Any, List
import time
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from itsdangerous import BadSignature, SignatureExpired
import db
import scoring
import tzi_trener
from .. import questions
from ..questions import verify_answer
from ..sessions import require_user
from ..config import serializer
from ..csrf import validate_csrf

router = APIRouter()

# Sledování použitých match tokenů proti replay útokům (token_sig -> expire_timestamp)
_CONSUMED_MATCH_TOKENS: Dict[str, float] = {}

def _clean_expired_tokens():
    now = time.time()
    expired = [k for k, exp in _CONSUMED_MATCH_TOKENS.items() if exp < now]
    for k in expired:
        _CONSUMED_MATCH_TOKENS.pop(k, None)


def _generate_match_token(user_id: int, mode: str, question_ids: List[str]) -> str:
    payload = {
        "uid": int(user_id),
        "mode": str(mode),
        "q_ids": [str(qid) for qid in question_ids],
        "ts": time.time(),
    }
    return serializer.dumps(payload, salt="tzi_match_token")


def _verify_and_consume_match_token(token: Optional[str], user_id: int, mode: str, submitted_qids: List[str]) -> Dict[str, Any]:
    # Fail-closed: match_token je pro soutěžní režimy povinný.
    # Bez něj nelze ověřit, že odpovídané otázky patří k vygenerovanému zápasu.
    if not token or not isinstance(token, str):
        raise HTTPException(status_code=400, detail="Chybí autorizační match_token pro herní relaci.")

    _clean_expired_tokens()
    if token in _CONSUMED_MATCH_TOKENS:
        raise HTTPException(status_code=400, detail="Tento zápas již byl odeslán (opakované použití tokenu zakázáno).")

    try:
        # Match session expiruje za 20 minut (1200 s)
        data = serializer.loads(token, salt="tzi_match_token", max_age=1200)
    except SignatureExpired:
        raise HTTPException(status_code=400, detail="Platnost herní relace vypršela.")
    except BadSignature:
        raise HTTPException(status_code=400, detail="Neplatný podpis herní relace (match_token).")

    if int(data.get("uid", 0)) != int(user_id):
        raise HTTPException(status_code=403, detail="Tento herní token patří jinému uživateli.")

    if str(data.get("mode", "")) != str(mode):
        raise HTTPException(status_code=400, detail="Herní režim neodpovídá vydanému tokenu.")

    issued_qids = set(str(qid) for qid in data.get("q_ids", []))
    for sq in submitted_qids:
        if str(sq) not in issued_qids:
            raise HTTPException(status_code=400, detail=f"Otázka {sq} nebyla pro tento zápas vygenerována.")

    return data


def _mark_match_token_consumed(token: Optional[str]) -> None:
    if token:
        _CONSUMED_MATCH_TOKENS[token] = time.time() + 1200


# --- King of the Hill (FFA / 1v1) Endpoints ---
@router.get("/api/koth/status")
def api_koth_status(user: Dict[str, Any] = Depends(require_user)):
    return scoring.get_koth_status()


@router.get("/api/koth/leaderboard")
def api_koth_leaderboard(user: Dict[str, Any] = Depends(require_user)):
    return scoring.get_koth_status()


@router.post("/api/koth/start")
async def api_koth_start(request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)):
    await validate_csrf(request, response, rotate=False)
    import random
    count = scoring.KOTH_DEFAULT_QUESTIONS
    source = ""
    try:
        body = await request.json()
        if isinstance(body, dict):
            count = max(1, min(30, int(body.get("count", count))))
            source = str(body.get("source", ""))
    except Exception:
        pass

    try:
        pool = tzi_trener.load_questions(source or tzi_trener.ALL)
    except Exception:
        pool = list(questions.ALL_QUESTIONS.values())

    eligible = [q for q in pool if not q.get("reveal")]
    picked = random.sample(eligible, min(count, len(eligible))) if eligible else []
    status = scoring.get_koth_status()
    uid = user.get("user_id") or 0
    token = _generate_match_token(uid, "koth", [str(q["id"]) for q in picked if "id" in q])
    return {
        "ok": True,
        "questions": picked,
        "match_token": token,
        "king": status["king"],
        "status": status
    }


@router.post("/api/koth/submit")
async def api_koth_submit(request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)):
    await validate_csrf(request, response, rotate=False)
    user_id = user["user_id"]
    if user.get("role") == "trial" or user_id == 0:
        raise HTTPException(status_code=403, detail="Pro souboj o Krále kopce je nutné se přihlásit.")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Neplatný JSON")

    correct_count, total_q, time_ms, q_ids, eval_results = _parse_competitive_submission(payload)
    token_to_consume = payload.get("match_token")
    _verify_and_consume_match_token(token_to_consume, user_id, "koth", q_ids)

    user_db = db.get_user_by_id(user_id)
    username = user_db["username"] if user_db else user.get("username", "Student")
    _record_competitive_answers(user_id, eval_results)

    res = scoring.submit_koth_challenge(
        user_id=user_id,
        username=username,
        correct_count=correct_count,
        total_questions=total_q,
        time_ms=time_ms
    )
    _mark_match_token_consumed(token_to_consume)
    return res


def _parse_competitive_submission(payload: Dict[str, Any]):
    answers = payload.get("answers")
    if not isinstance(answers, list) or len(answers) == 0:
        raise HTTPException(status_code=400, detail="Pole answers je povinné.")

    try:
        raw_time = payload.get("time_ms", 0)
        time_ms = max(0, int(0 if raw_time is None else raw_time))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Neplatný čas (time_ms).")

    correct_count = 0
    question_ids = []
    eval_results = []
    seen_qids = set()

    for item in answers:
        if not isinstance(item, dict):
            continue
        q_id = str(item.get("id", ""))
        if not q_id or q_id in seen_qids:
            continue
        seen_qids.add(q_id)
        question_ids.append(q_id)
        q = questions.ALL_QUESTIONS.get(q_id)
        u_ans = item.get("userKeys") if item.get("userKeys") is not None else item.get("user_answer")
        is_ok = verify_answer(q, u_ans) if (q and u_ans is not None) else False
        if is_ok:
            correct_count += 1
        eval_results.append((q_id, is_ok))

    total_q = max(len(seen_qids), scoring.KOTH_DEFAULT_QUESTIONS)
    return correct_count, total_q, time_ms, question_ids, eval_results


def _record_competitive_answers(user_id: int, eval_results: List[tuple]) -> None:
    for q_id, is_ok in eval_results:
        if q_id:
            scoring.record_question_answer(user_id, q_id, is_ok)


@router.get("/api/competitive/overview")
def api_competitive_overview(user: Dict[str, Any] = Depends(require_user)):
    uid = user.get("user_id") or 0
    return {
        "ffa": scoring.get_ffa_status(),
        "duel": scoring.get_duel_status(uid),
        "koth": scoring.get_koth_status(),
        "rooms": scoring.list_comp_rooms(uid)
    }


def _resolve_room_questions(room: Optional[Dict[str, Any]]) -> list:
    if not room:
        return []
    q_ids = room.get("question_ids") or []
    picked = [questions.ALL_QUESTIONS[str(qid)] for qid in q_ids if str(qid) in questions.ALL_QUESTIONS]
    if not picked:
        import random
        src = room.get("source") or ""
        cnt = int(room.get("question_count") or scoring.KOTH_DEFAULT_QUESTIONS)
        try:
            pool = tzi_trener.load_questions(src or tzi_trener.ALL)
        except Exception:
            pool = list(questions.ALL_QUESTIONS.values())
        eligible = [q for q in pool if not q.get("reveal")]
        picked = random.sample(eligible, min(cnt, len(eligible))) if eligible else []
    return picked


@router.get("/api/rooms")
def api_rooms_list(user: Dict[str, Any] = Depends(require_user)):
    uid = user.get("user_id") or 0
    return scoring.list_comp_rooms(uid)


@router.post("/api/rooms/create")
async def api_rooms_create(request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)):
    await validate_csrf(request, response, rotate=False)
    import random
    uid = user.get("user_id") or 0
    if user.get("role") == "trial" or uid == 0:
        raise HTTPException(status_code=403, detail="Pro vytvoření místnosti v lobby je nutné se přihlásit.")

    mode = "ffa"
    name = ""
    count = scoring.KOTH_DEFAULT_QUESTIONS
    source = ""
    max_players = None
    try:
        body = await request.json()
        if isinstance(body, dict):
            mode = str(body.get("mode", "ffa"))
            name = str(body.get("name", ""))
            count = max(1, min(30, int(body.get("count", count))))
            source = str(body.get("source", ""))
            if body.get("max_players") is not None:
                max_players = int(body.get("max_players"))
    except Exception:
        pass

    try:
        pool = tzi_trener.load_questions(source or tzi_trener.ALL)
    except Exception:
        pool = list(questions.ALL_QUESTIONS.values())
    eligible = [q for q in pool if not q.get("reveal")]
    picked = random.sample(eligible, min(count, len(eligible))) if eligible else []
    q_ids = [str(q["id"]) for q in picked if "id" in q]

    user_db = db.get_user_by_id(uid)
    username = user_db["username"] if user_db else user.get("username", "Student")

    room = scoring.create_comp_room(
        user_id=uid,
        username=username,
        mode=mode,
        name=name,
        question_count=len(picked) or count,
        source=source,
        question_ids=q_ids,
        max_players=max_players,
    )
    return {"ok": True, "room": room, "questions": picked}


@router.get("/api/rooms/{room_id}")
def api_room_detail(room_id: int, user: Dict[str, Any] = Depends(require_user)):
    room = scoring.get_comp_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Místnost neexistuje.")
    uid = user.get("user_id") or 0
    is_member = any(p.get("user_id") == uid for p in (room.get("players") or []))
    room_qs = _resolve_room_questions(room) if (is_member and room.get("status") in ("in_progress", "completed")) else []
    return {"ok": True, "room": room, "questions": room_qs}


@router.post("/api/rooms/{room_id}/join")
async def api_room_join(room_id: int, request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)):
    await validate_csrf(request, response, rotate=False)
    uid = user.get("user_id") or 0
    if user.get("role") == "trial" or uid == 0:
        raise HTTPException(status_code=403, detail="Pro připojení do místnosti je nutné se přihlásit.")

    auto_start_duel = False
    try:
        body = await request.json()
        if isinstance(body, dict):
            auto_start_duel = bool(body.get("auto_start_duel", False))
    except Exception:
        pass

    user_db = db.get_user_by_id(uid)
    username = user_db["username"] if user_db else user.get("username", "Student")
    res = scoring.join_comp_room(room_id, uid, username, auto_start_duel=auto_start_duel)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error", "Nelze se připojit do místnosti."))
    room = res["room"]
    questions = _resolve_room_questions(room) if room.get("status") == "in_progress" else []
    return {"ok": True, "room": room, "questions": questions}


@router.post("/api/rooms/{room_id}/start")
async def api_room_start(room_id: int, request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)):
    await validate_csrf(request, response, rotate=False)
    uid = user.get("user_id") or 0
    if user.get("role") == "trial" or uid == 0:
        raise HTTPException(status_code=403, detail="Nepřihlášený uživatel nemůže spustit místnost.")
    res = scoring.start_comp_room(room_id, uid)
    if not res.get("ok"):
        raise HTTPException(status_code=403, detail=res.get("error", "Nelze spustit místnost."))
    room = res["room"]
    room_qs = _resolve_room_questions(room)
    return {"ok": True, "room": room, "questions": room_qs}


@router.post("/api/rooms/{room_id}/leave")
async def api_room_leave(room_id: int, request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)):
    await validate_csrf(request, response, rotate=False)
    uid = user.get("user_id") or 0
    return scoring.leave_comp_room(room_id, uid)


@router.post("/api/rooms/{room_id}/submit")
async def api_room_submit(room_id: int, request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)):
    await validate_csrf(request, response, rotate=False)
    uid = user.get("user_id") or 0
    if user.get("role") == "trial" or uid == 0:
        raise HTTPException(status_code=403, detail="Pro odeslání výsledku v místnosti je nutné se přihlásit.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Neplatný JSON")

    # Validace odpovědí v paměti BEZ zápisu do DB, pak validace místnosti a členství
    correct_count, total_q, time_ms, submitted_qids, eval_results = _parse_competitive_submission(payload)

    room = scoring.get_comp_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Místnost neexistuje.")

    if room.get("status") != "in_progress":
        raise HTTPException(status_code=400, detail="Místnost není ve stavu in_progress (nebyla zahájena).")

    players = room.get("players", [])
    player_ids = [p["user_id"] for p in players] if players else []
    if uid not in player_ids:
        raise HTTPException(status_code=403, detail="Nejste hráčem této místnosti.")

    room_qids = set(str(qid) for qid in (room.get("question_ids") or []))
    if room_qids:
        if not submitted_qids:
            raise HTTPException(status_code=400, detail="Nebyly odeslány žádné odpovědi.")
        for sq in submitted_qids:
            if str(sq) not in room_qids:
                raise HTTPException(status_code=400, detail=f"Otázka {sq} nepatří do této místnosti.")

    user_db = db.get_user_by_id(uid)
    username = user_db["username"] if user_db else user.get("username", "Student")
    _record_competitive_answers(uid, eval_results)

    res = scoring.submit_comp_room_result(
        room_id=room_id,
        user_id=uid,
        username=username,
        correct_count=correct_count,
        total_questions=total_q,
        time_ms=time_ms,
    )
    if not res.get("ok"):
        raise HTTPException(status_code=404, detail=res.get("error", "Místnost neexistuje."))
    return res


@router.get("/api/ffa/status")
def api_ffa_status(user: Dict[str, Any] = Depends(require_user)):
    return scoring.get_ffa_status()


@router.post("/api/ffa/start")
async def api_ffa_start(request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)):
    await validate_csrf(request, response, rotate=False)
    import random
    count = scoring.KOTH_DEFAULT_QUESTIONS
    source = ""
    try:
        body = await request.json()
        if isinstance(body, dict):
            count = max(1, min(30, int(body.get("count", count))))
            source = str(body.get("source", ""))
    except Exception:
        pass
    try:
        pool = tzi_trener.load_questions(source or tzi_trener.ALL)
    except Exception:
        pool = list(questions.ALL_QUESTIONS.values())
    eligible = [q for q in pool if not q.get("reveal")]
    picked = random.sample(eligible, min(count, len(eligible))) if eligible else []
    uid = user.get("user_id") or 0
    token = _generate_match_token(uid, "ffa", [str(q["id"]) for q in picked if "id" in q])
    return {"ok": True, "mode": "ffa", "questions": picked, "match_token": token, "status": scoring.get_ffa_status()}


@router.post("/api/ffa/submit")
async def api_ffa_submit(request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)):
    await validate_csrf(request, response, rotate=False)
    user_id = user["user_id"]
    if user.get("role") == "trial" or user_id == 0:
        raise HTTPException(status_code=403, detail="Pro účast ve Free For All aréně je nutné se přihlásit.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Neplatný JSON")

    correct_count, total_q, time_ms, q_ids, eval_results = _parse_competitive_submission(payload)
    if time_ms < 5000:
        raise HTTPException(status_code=400, detail="Čas dokončení je příliš krátký (minimálně 5 sekund).")
    token_to_consume = payload.get("match_token")
    _verify_and_consume_match_token(token_to_consume, user_id, "ffa", q_ids)

    user_db = db.get_user_by_id(user_id)
    username = user_db["username"] if user_db else user.get("username", "Student")
    _record_competitive_answers(user_id, eval_results)

    res = scoring.submit_ffa_run(
        user_id=user_id,
        username=username,
        correct_count=correct_count,
        total_questions=total_q,
        time_ms=time_ms
    )
    _mark_match_token_consumed(token_to_consume)
    return res


@router.get("/api/duel/status")
def api_duel_status(user: Dict[str, Any] = Depends(require_user)):
    return scoring.get_duel_status(user.get("user_id") or 0)


@router.post("/api/duel/start")
async def api_duel_start(request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)):
    await validate_csrf(request, response, rotate=False)
    import random
    uid = user.get("user_id") or 0
    count = scoring.KOTH_DEFAULT_QUESTIONS
    source = ""
    duel_id = None
    opponent_id = None
    try:
        body = await request.json()
        if isinstance(body, dict):
            count = max(1, min(30, int(body.get("count", count))))
            source = str(body.get("source", ""))
            duel_id = body.get("duel_id")
            opponent_id = body.get("opponent_id")
    except Exception:
        pass

    if opponent_id is not None:
        try:
            opponent_id_val = int(opponent_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Neplatné opponent_id.")
        if opponent_id_val == uid:
            raise HTTPException(status_code=400, detail="Nelze vyzvat sám sebe.")

    conn = db.get_db()
    open_row = None
    if duel_id is not None:
        try:
            duel_id_val = int(duel_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Neplatné duel_id.")
        open_row = conn.execute("SELECT * FROM duel_matches WHERE id = ? AND status = 'open'", (duel_id_val,)).fetchone()
        if open_row is not None and open_row["creator_id"] == uid:
            raise HTTPException(status_code=400, detail="Nelze vyzvat sám sebe.")
    if open_row is None and uid > 0:
        open_row = conn.execute("SELECT * FROM duel_matches WHERE status = 'open' AND creator_id != ? ORDER BY id ASC LIMIT 1", (uid,)).fetchone()

    picked = []
    matched_duel = None
    if open_row is not None and open_row["creator_id"] != uid:
        try:
            q_ids = json.loads(open_row["question_ids_json"] or "[]")
            picked = [questions.ALL_QUESTIONS[str(qid)] for qid in q_ids if str(qid) in questions.ALL_QUESTIONS]
        except Exception:
            picked = []
        matched_duel = {
            "id": open_row["id"],
            "creator_username": open_row["creator_username"],
            "creator_score": open_row["creator_score"]
        }

    if not picked:
        try:
            pool = tzi_trener.load_questions(source or tzi_trener.ALL)
        except Exception:
            pool = list(questions.ALL_QUESTIONS.values())
        eligible = [q for q in pool if not q.get("reveal")]
        picked = random.sample(eligible, min(count, len(eligible))) if eligible else []

    token = _generate_match_token(uid, "duel", [str(q["id"]) for q in picked if "id" in q])
    return {
        "ok": True,
        "mode": "duel",
        "duel": matched_duel,
        "questions": picked,
        "match_token": token,
        "status": scoring.get_duel_status(uid)
    }


@router.post("/api/duel/submit")
async def api_duel_submit(request: Request, response: Response, user: Dict[str, Any] = Depends(require_user)):
    await validate_csrf(request, response, rotate=False)
    user_id = user["user_id"]
    if user.get("role") == "trial" or user_id == 0:
        raise HTTPException(status_code=403, detail="Pro 1v1 souboj je nutné se přihlásit.")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Neplatný JSON")

    duel_id = payload.get("duel_id")
    duel_id_val = None
    if duel_id is not None:
        try:
            duel_id_val = int(duel_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Neplatné duel_id.")

    correct_count, total_q, time_ms, q_ids, eval_results = _parse_competitive_submission(payload)
    token_to_consume = payload.get("match_token")
    _verify_and_consume_match_token(token_to_consume, user_id, "duel", q_ids)

    user_db = db.get_user_by_id(user_id)
    username = user_db["username"] if user_db else user.get("username", "Student")
    _record_competitive_answers(user_id, eval_results)

    res = scoring.submit_duel_match(
        user_id=user_id,
        username=username,
        correct_count=correct_count,
        total_questions=total_q,
        time_ms=time_ms,
        question_ids=q_ids,
        duel_id=duel_id_val,
    )
    _mark_match_token_consumed(token_to_consume)
    return res
