"""Edge-case unit & integration tests across auth, CSRF, study/sync, competitive, rooms, and admin."""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import db
import server
from webapp import questions
from webapp.routers import auth, pwa, study


@pytest.fixture()
def iso_db(tmp_path):
    """Provide isolated SQLite DB and clean rate-limiter state per test."""
    db.close_db()
    old_db = db.DB_FILE
    db.DB_FILE = tmp_path / "edge_cases.db"
    db.init_db()
    questions.refresh_questions()
    auth._rate_limit_store.clear()
    study.reset_progress_rate_limits()
    study.reset_sync_rate_limits()
    study.reset_client_error_rate_limits()
    yield
    db.close_db()
    db.DB_FILE = old_db


def _register_browser_client(username: str, ua: str = "EdgeBrowser/1.0") -> tuple[TestClient, str]:
    c = TestClient(server.app, headers={"User-Agent": ua})
    csrf = c.get("/register").cookies.get("csrf_token")
    r = c.post(
        "/register",
        data={
            "username": username,
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "csrf_token": csrf,
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    return c, c.cookies.get("csrf_token")


def test_auth_and_session_edge_cases(iso_db):
    c = TestClient(server.app, headers={"User-Agent": "EdgeBrowser/1.0"})
    csrf = c.get("/register").cookies.get("csrf_token")

    # Non-ASCII CSRF token in form must return 403, never 500
    r_non_ascii = c.post(
        "/login",
        data={"username": "x", "password": "y", "csrf_token": "čřž"},
        follow_redirects=False,
    )
    assert r_non_ascii.status_code == 403

    # Missing CSRF token on real browser UA must return 403
    r_missing = c.post("/login", data={"username": "x", "password": "y"}, follow_redirects=False)
    assert r_missing.status_code == 403

    # Registration validation boundaries
    for payload in (
        {"username": "validuser", "password": "123", "password_confirm": "123"},
        {"username": "validuser", "password": "StrongPassword123!", "password_confirm": "Mismatch123!"},
        {"username": "a", "password": "StrongPassword123!", "password_confirm": "StrongPassword123!"},
        {"username": "ab", "password": "StrongPassword123!", "password_confirm": "StrongPassword123!"},
        {"username": "x" * 26, "password": "StrongPassword123!", "password_confirm": "StrongPassword123!"},
        {"username": "Admin", "password": "StrongPassword123!", "password_confirm": "StrongPassword123!"},
        {"username": "bad$name!", "password": "StrongPassword123!", "password_confirm": "StrongPassword123!"},
    ):
        r = c.post("/register", data={**payload, "csrf_token": csrf}, follow_redirects=False)
        assert r.status_code == 303
        assert "/register?error=" in r.headers["location"], payload
        csrf = c.cookies.get("csrf_token") or csrf

    # Secure cookie flag toggles based on X-Forwarded-Proto
    r_http = c.get("/trial", follow_redirects=False)
    assert "Secure" not in r_http.headers.get("set-cookie", "")
    r_https = c.get("/trial", headers={"X-Forwarded-Proto": "https"}, follow_redirects=False)
    set_cookies = r_https.headers.get_list("set-cookie")
    assert any("tzi_session=" in sc and "Secure" in sc and "HttpOnly" in sc for sc in set_cookies)


def test_verify_answer_and_study_sync_edge_cases(iso_db):
    # Choice: order-independent, partial/extra fail
    q_choice = {"type": "choice", "correct": ["A", "C"]}
    assert questions.verify_answer(q_choice, ["C", "A"]) is True
    assert questions.verify_answer(q_choice, ["A"]) is False
    assert questions.verify_answer(q_choice, ["A", "C", "D"]) is False
    assert questions.verify_answer(q_choice, None) is False

    # Input: leading zeros, whitespace, underscores, empty
    q_input = {"type": "input", "answer": "042"}
    assert questions.verify_answer(q_input, "42") is True
    assert questions.verify_answer(q_input, " 0042 ") is True
    assert questions.verify_answer(q_input, "4_2") is True
    assert questions.verify_answer(q_input, "") is False

    # Recall: Lev1 typo tolerance (>5 chars, same first char) vs empty
    q_recall = {"type": "recall", "accept": ["komplement"]}
    assert questions.verify_answer(q_recall, "komplemnt") is True
    assert questions.verify_answer(q_recall, "xomplement") is False
    assert questions.verify_answer(q_recall, "   ") is False

    # Trial progress & sync must not write points; bad payloads rejected cleanly
    trial = TestClient(server.app, headers={"User-Agent": "EdgeBrowser/1.0"})
    trial.get("/trial", follow_redirects=False)
    t_csrf = trial.cookies.get("csrf_token")
    assert trial.post("/api/progress", json={"seen": {}}, headers={"X-CSRF-Token": t_csrf}).json() == {"ok": True, "score": None}
    assert trial.post("/api/sync", json={"answers": []}, headers={"X-CSRF-Token": t_csrf}).json()["synced_count"] == 0

    stu, csrf = _register_browser_client("edge_study_u1")
    # Bad JSON / non-list answers / unknown qid / spoofed isCorrect
    assert stu.post("/api/progress", content=b"{bad", headers={"X-CSRF-Token": csrf, "Content-Type": "application/json"}).status_code == 400
    assert stu.post("/api/progress", json={"latest": {"id": "no_such_q", "userKeys": ["A"]}}, headers={"X-CSRF-Token": csrf}).status_code == 400
    assert stu.post("/api/progress", json={"latest": {"id": "1-1", "isCorrect": True}}, headers={"X-CSRF-Token": csrf}).status_code == 400
    assert stu.post("/api/sync", json={"answers": "not-a-list"}, headers={"X-CSRF-Token": csrf}).status_code == 400

    # Batch >100 items capped at 100 and duplicate q_ids deduplicated
    all_qs = stu.get("/api/questions?source=_all").json()
    batch = [{"id": q["id"], "userKeys": q.get("correct") or q.get("answer")} for q in all_qs if not q.get("reveal")]
    padded = [batch[0], batch[0]] + batch[:120]
    res = stu.post("/api/sync", json={"answers": padded, "source": "_all"}, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    assert res.json()["synced_count"] <= 100

    # /api/teorie boundary inputs
    assert stu.get("/api/teorie?source=").status_code == 400
    assert stu.get(f"/api/teorie?source={'a' * 65}").status_code == 400
    assert stu.get("/api/teorie?source=bad/path").status_code == 400
    r404 = stu.get("/api/teorie?source=missing_lecture")
    assert r404.status_code == 404 and r404.json()["detail"] == "Zdroj nebyl nalezen"


def test_competitive_and_room_edge_cases(iso_db):
    c1, csrf1 = _register_browser_client("edge_comp_u1", "UA1/1.0")
    c2, csrf2 = _register_browser_client("edge_comp_u2", "UA2/1.0")
    c3, csrf3 = _register_browser_client("edge_comp_u3", "UA3/1.0")

    qs = [q for q in c1.get("/api/questions?source=01-2026-10-01").json() if q.get("type") == "choice"]
    q0, q1 = qs[0], qs[1]

    # Negative, zero, and >64-bit SQLite room IDs never trigger 500
    for bad_id in ("0", "-5", "9223372036854775808"):
        assert c1.get(f"/api/rooms/{bad_id}").status_code == 404
        assert c1.post(f"/api/rooms/{bad_id}/join", headers={"X-CSRF-Token": csrf1}).status_code == 400
        assert c1.post(f"/api/rooms/{bad_id}/start", headers={"X-CSRF-Token": csrf1}).status_code == 403
        assert c1.post(f"/api/rooms/{bad_id}/leave", headers={"X-CSRF-Token": csrf1}).status_code == 200
        assert c1.post(
            f"/api/rooms/{bad_id}/submit",
            json={"answers": [{"id": q0["id"], "userKeys": q0["correct"]}], "time_ms": 5000},
            headers={"X-CSRF-Token": csrf1},
        ).status_code == 404

    # Duel ID / opponent_id bounds
    for bad_duel in (True, 0, -1, 9223372036854775808, "abc"):
        assert c1.post("/api/duel/start", json={"duel_id": bad_duel}, headers={"X-CSRF-Token": csrf1}).status_code == 400
        assert c1.post("/api/duel/start", json={"opponent_id": bad_duel}, headers={"X-CSRF-Token": csrf1}).status_code == 400

    # Cross-user and cross-mode match_token rejection without awarding XP
    k1 = c1.post("/api/koth/start", json={"count": 3, "source": "01-2026-10-01"}, headers={"X-CSRF-Token": csrf1}).json()
    kq = k1["questions"][0]
    kans = kq.get("correct") if kq.get("correct") is not None else kq.get("answer")
    pts2_before = c2.get("/api/me").json()["points"]
    assert c2.post(
        "/api/koth/submit",
        json={"answers": [{"id": kq["id"], "userKeys": kans}], "time_ms": 6000, "match_token": k1["match_token"]},
        headers={"X-CSRF-Token": csrf2},
    ).status_code == 403
    assert c1.post(
        "/api/duel/submit",
        json={"answers": [{"id": kq["id"], "userKeys": kans}], "time_ms": 6000, "match_token": k1["match_token"]},
        headers={"X-CSRF-Token": csrf1},
    ).status_code == 400
    assert c2.get("/api/me").json()["points"] == pts2_before

    # Huge and negative time_ms clamped safely (negative -> 0 -> fails FFA <5000ms)
    ffa1 = c1.post("/api/ffa/start", json={"count": 3, "source": "01-2026-10-01"}, headers={"X-CSRF-Token": csrf1}).json()
    fq = ffa1["questions"][0]
    fans = fq.get("correct") if fq.get("correct") is not None else fq.get("answer")
    assert c1.post(
        "/api/ffa/submit",
        json={"answers": [{"id": fq["id"], "userKeys": fans}], "time_ms": -500, "match_token": ffa1["match_token"]},
        headers={"X-CSRF-Token": csrf1},
    ).status_code == 400
    assert c1.post(
        "/api/ffa/submit",
        json={"answers": [{"id": fq["id"], "userKeys": fans}], "time_ms": 99999999999999999999, "match_token": ffa1["match_token"]},
        headers={"X-CSRF-Token": csrf1},
    ).status_code == 200

    # Room capacity, non-host start, host crown transfer, and final cleanup
    room = c1.post(
        "/api/rooms/create",
        json={"mode": "ffa", "name": "TwoMax", "count": 3, "max_players": 2, "source": "01-2026-10-01"},
        headers={"X-CSRF-Token": csrf1},
    ).json()["room"]
    rid = room["id"]
    assert c2.post(f"/api/rooms/{rid}/join", headers={"X-CSRF-Token": csrf2}).status_code == 200
    assert c3.post(f"/api/rooms/{rid}/join", headers={"X-CSRF-Token": csrf3}).status_code == 400
    assert c2.post(f"/api/rooms/{rid}/start", headers={"X-CSRF-Token": csrf2}).status_code == 403
    # Host leaves -> c2 becomes host and can start; then c2 leaves -> room deleted
    leave1 = c1.post(f"/api/rooms/{rid}/leave", headers={"X-CSRF-Token": csrf1}).json()
    assert leave1["deleted"] is False
    assert c2.post(f"/api/rooms/{rid}/start", headers={"X-CSRF-Token": csrf2}).status_code == 200
    leave2 = c2.post(f"/api/rooms/{rid}/leave", headers={"X-CSRF-Token": csrf2}).json()
    assert leave2["deleted"] is True
    assert c2.get(f"/api/rooms/{rid}").status_code == 404


def test_admin_account_and_webhook_edge_cases(iso_db, monkeypatch):
    monkeypatch.setattr(pwa, "WEBHOOK_SECRET", "ascii_secret_999")
    stu, csrf_stu = _register_browser_client("edge_acct_u1", "AcctUA/1.0")

    # Trial & student blocked from admin routes
    assert stu.get("/admin").status_code == 403
    assert stu.post("/admin/leaderboard/reset", data={"user_id": "1", "scope": "all", "csrf_token": csrf_stu}).status_code == 403

    # Admin user_id bounds (0 / >64-bit) rejected with 400, not 500
    adm = TestClient(server.app, headers={"User-Agent": "AdminUA/1.0"})
    adm_csrf = adm.get("/login").cookies.get("csrf_token")
    from webapp.config import HASHED_PASSWORD
    db.ensure_admin_exists(HASHED_PASSWORD)
    adm_token = server.create_session_token({"id": 1, "username": "admin", "role": "admin", "theme": "games"})
    adm.cookies.set(server.SESSION_COOKIE, adm_token)
    adm_csrf = adm.cookies.get("csrf_token") or adm_csrf
    assert adm.post("/admin/leaderboard/toggle", data={"user_id": "0", "csrf_token": adm_csrf}).status_code == 400
    assert adm.post("/admin/leaderboard/reset", data={"user_id": "9223372036854775808", "scope": "all", "csrf_token": adm_csrf}).status_code == 400

    # Account delete-profile guard rails
    me_u = stu.get("/api/me").json()
    assert stu.post("/api/account/delete-profile", json={"step1_ack": False, "confirm_username": me_u["username"], "confirm_phrase": "DELETE", "password": "StrongPassword123!"}, headers={"X-CSRF-Token": csrf_stu}).status_code == 400
    assert stu.post("/api/account/delete-profile", json={"step1_ack": True, "confirm_username": "wrong", "confirm_phrase": "DELETE", "password": "StrongPassword123!"}, headers={"X-CSRF-Token": csrf_stu}).status_code == 400
    assert stu.post("/api/account/delete-profile", json={"step1_ack": True, "confirm_username": me_u["username"], "confirm_phrase": "NOPE", "password": "StrongPassword123!"}, headers={"X-CSRF-Token": csrf_stu}).status_code == 400
    assert stu.post("/api/account/delete-profile", json={"step1_ack": True, "confirm_username": me_u["username"], "confirm_phrase": "DELETE", "password": "WrongPassword!"}, headers={"X-CSRF-Token": csrf_stu}).status_code == 403
    r_del = stu.post("/api/account/delete-profile", json={"step1_ack": True, "confirm_username": me_u["username"], "confirm_phrase": "DELETE", "password": "StrongPassword123!"}, headers={"X-CSRF-Token": csrf_stu})
    assert r_del.status_code == 200 and r_del.json()["ok"] is True

    # Webhook empty/wrong/non-ASCII secret
    assert stu.post("/webhook").status_code == 403
    assert stu.post("/webhook?secret=wrong").status_code == 403
    assert stu.post("/webhook?secret=%C4%8D%C5%99%C5%BE").status_code == 403
