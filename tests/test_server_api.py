import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from fastapi.testclient import TestClient
import server
import db

def _cleanup_db(db_path: Path):
    db.close_db()
    for ext in ("", "-shm", "-wal"):
        f = Path(str(db_path) + ext)
        try:
            if f.exists():
                f.unlink()
        except Exception:
            pass


def test_full_pipeline():
    test_db = BASE / "test_temp_api.db"
    _cleanup_db(test_db)
    db.DB_FILE = test_db
    db.init_db()

    client = TestClient(server.app)

    print("--- [1] Test GET / unauthenticated -> Redirect to /login ---")
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 307 or r.status_code == 302 or r.status_code == 303, f"Status: {r.status_code}"
    assert "/login" in r.headers["location"]
    print("OK: Nepřihlášený uživatel přesměrován na /login.")

    print("\n--- [2] Test GET /login & /register ---")
    r_login = client.get("/login")
    assert r_login.status_code == 200
    assert "TZI Trenér" in r_login.text

    r_reg = client.get("/register")
    assert r_reg.status_code == 200
    assert "Registrace" in r_reg.text
    assert 'name="invite_code"' not in r_reg.text
    print("OK: Stránky pro přihlášení a registraci (bez pozvánky) fungují.")

    print("\n--- [3] Otevřená registrace nového studenta bez pozvánky ---")
    csrf_token = r_reg.cookies.get("csrf_token")
    reg_resp = client.post("/register", data={
        "theme": "movies",
        "password": "mypassword123",
        "csrf_token": csrf_token
    }, follow_redirects=False)
    assert reg_resp.status_code == 303, f"Status: {reg_resp.status_code}"
    cookie = reg_resp.cookies.get(server.SESSION_COOKIE)
    assert cookie is not None, "Session cookie musí být nastavena po registraci!"
    print("OK: Registrace proběhla, session cookie nastavena.")

    print("\n--- [4] Test přihlášeného studenta: GET /api/me ---")
    client.cookies.set(server.SESSION_COOKIE, cookie)
    me_resp = client.get("/api/me")
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    print(f"Přiřazená přezdívka: {me_data['username']} (Téma: {me_data['theme']})")
    assert me_data["rank"] >= 1

    print("\n--- [5] Test kvízových API (/api/sources, /api/questions, /api/recall) ---")
    s_resp = client.get("/api/sources")
    assert s_resp.status_code == 200
    sources = s_resp.json()["sources"]
    print(f"Počet zdrojů přednášek: {len(sources)}")
    assert len(sources) > 0

    first_src = sources[0]["id"]
    q_resp = client.get(f"/api/questions?source={first_src}")
    assert q_resp.status_code == 200
    questions = q_resp.json()
    print(f"Otázek v {first_src}: {len(questions)}")

    print("\n--- [6] Test odeslání odpovědi s výpočtem bodů (POST /api/progress) ---")
    test_q = questions[0] if questions else {"id": "test_q", "correct": ["A"]}
    test_q_id = test_q["id"]
    test_correct = test_q.get("correct") or test_q.get("answer") or ["A"]
    prog_resp = client.post("/api/progress?source=" + first_src, json={
        "seen": {test_q_id: "correct"},
        "session": None,
        "latest": {"id": test_q_id, "userKeys": test_correct}
    })
    assert prog_resp.status_code == 200
    prog_data = prog_resp.json()
    assert prog_data["ok"] is True
    assert prog_data["score"] is not None
    assert prog_data["score"]["points_awarded"] == 3
    print(f"OK: Získáno {prog_data['score']['points_awarded']} b, streak: {prog_data['score']['streak']}")

    print("\n--- [7] Test Leaderboard endpointu (/api/leaderboard) ---")
    lb_resp = client.get("/api/leaderboard")
    assert lb_resp.status_code == 200
    lb_data = lb_resp.json()
    print(f"Leaderboard: #{lb_data['rank']} z {lb_data['total']} studentů ({lb_data['points']} b)")
    assert lb_data["points"] == 3

    print("\n--- [8] Test PWA endpointů (/manifest.webmanifest, /sw.js, /icon.svg) ---")
    r_man = client.get("/manifest.webmanifest")
    assert r_man.status_code == 200
    assert "TZI Trenér" in r_man.json()["name"]

    r_sw = client.get("/sw.js")
    assert r_sw.status_code == 200
    assert "CACHE_NAME" in r_sw.text

    r_icon = client.get("/icon.svg")
    assert r_icon.status_code == 200
    assert "<svg" in r_icon.text
    print("OK: PWA manifest, service worker a ikona fungují.")

    print("\n--- [9] Test Offline Sync s Anti-spoofing kontrolou (/api/sync) ---")
    # Zkusíme poslat odpověď: jedna správná a jedna zfalšovaná (špatná volba označená jako isCorrect=True)
    q_choice = [q for q in questions if q.get("type") == "choice"][0]
    q_id_choice = q_choice["id"]
    correct_opts = q_choice["correct"]

    # Falešná odpověď: uživatel pošle neplatnou volbu ['Z']
    sync_resp_fake = client.post("/api/sync", json={
        "source": first_src,
        "seen": {q_id_choice: "wrong"},
        "answers": [
            {"id": q_id_choice, "user_answer": ["Z"], "isCorrect": True}
        ]
    })
    assert sync_resp_fake.status_code == 200
    assert sync_resp_fake.json()["points_awarded"] == 0, "Anti-spoofing musí odmítnout body pro neplatnou odpověď!"

    # Pravá odpověď: uživatel pošle správnou volbu
    sync_resp_real = client.post("/api/sync", json={
        "source": first_src,
        "seen": {q_id_choice: "correct"},
        "answers": [
            {"id": q_id_choice, "user_answer": correct_opts, "isCorrect": True}
        ]
    })
    assert sync_resp_real.status_code == 200
    sync_data = sync_resp_real.json()
    assert sync_data["synced_count"] == 1
    assert sync_data["leaderboard"] is not None
    print(f"OK: Anti-spoofing ověření funguje. Body po synchronizaci: {sync_data['leaderboard']['points']} b.")

    print("\n=======================================================")
    print("  FASTAPI PIPELINE KOMPLETNĚ OTESTOVÁNA A FUNKČNÍ! :3 ")
    print("=======================================================")

    _cleanup_db(test_db)


def _setup_test_client_with_user():
    test_db = BASE / "test_temp_api_r.db"
    _cleanup_db(test_db)
    db.DB_FILE = test_db
    db.init_db()

    client = TestClient(server.app)
    r_reg = client.get("/register")
    csrf_token = r_reg.cookies.get("csrf_token")
    reg_resp = client.post("/register", data={
        "theme": "games",
        "password": "mypassword123",
        "csrf_token": csrf_token
    }, follow_redirects=False)
    cookie = reg_resp.cookies.get(server.SESSION_COOKIE)
    client.cookies.set(server.SESSION_COOKIE, cookie)
    return client, test_db


def test_r2_progress_anti_spoofing():
    """R2: /api/progress strictly requires userKeys/user_answer and server-verifies against question bank."""
    client, test_db = _setup_test_client_with_user()
    try:
        s_resp = client.get("/api/sources")
        assert s_resp.status_code == 200
        sources = s_resp.json()["sources"]
        assert len(sources) > 0
        src = sources[0]["id"]

        q_resp = client.get(f"/api/questions?source={src}")
        assert q_resp.status_code == 200
        questions_list = q_resp.json()
        assert len(questions_list) > 0
        q = questions_list[0]
        q_id = q["id"]
        correct_ans = q.get("correct") or q.get("answer")

        # 1. Reject missing userKeys and user_answer when latest is present
        resp = client.post(f"/api/progress?source={src}", json={
            "seen": {},
            "session": None,
            "latest": {"id": q_id, "isCorrect": True}
        })
        assert resp.status_code == 400
        assert "userKeys" in resp.json().get("detail", "") or "user_answer" in resp.json().get("detail", "")

        # 2. Reject missing id in latest
        resp = client.post(f"/api/progress?source={src}", json={
            "seen": {},
            "session": None,
            "latest": {"userKeys": ["A"]}
        })
        assert resp.status_code == 400

        # 3. Reject nonexistent question id
        resp = client.post(f"/api/progress?source={src}", json={
            "seen": {},
            "session": None,
            "latest": {"id": "nonexistent_question_99999", "userKeys": ["A"]}
        })
        assert resp.status_code == 400
        assert "Neznámá otázka" in resp.json().get("detail", "")

        # 4. Anti-spoofing: spoofed isCorrect=True with incorrect answer is rejected by server
        resp = client.post(f"/api/progress?source={src}", json={
            "seen": {},
            "session": None,
            "latest": {"id": q_id, "userKeys": ["DEFINITELY_WRONG_OPTION_XYZ"], "isCorrect": True}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["score"] is not None
        assert data["score"]["points_awarded"] == 0, "Spoofed answer must award 0 points"

        # 5. Legitimate correct answer awards points
        resp = client.post(f"/api/progress?source={src}", json={
            "seen": {q_id: "correct"},
            "session": None,
            "latest": {"id": q_id, "userKeys": correct_ans}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["score"]["points_awarded"] > 0

        # 6. user_answer field also accepted for legitimate answers
        if len(questions_list) > 1:
            q2 = questions_list[1]
            q2_id = q2["id"]
            q2_correct = q2.get("correct") or q2.get("answer")
            resp = client.post(f"/api/progress?source={src}", json={
                "seen": {q2_id: "correct"},
                "session": None,
                "latest": {"id": q2_id, "user_answer": q2_correct}
            })
            assert resp.status_code == 200
            assert resp.json()["score"]["points_awarded"] > 0

        # 7. Progress save without latest does not error and awards no score
        resp = client.post(f"/api/progress?source={src}", json={
            "seen": {"some_q": "wrong"},
            "session": None,
            "latest": None
        })
        assert resp.status_code == 200
        assert resp.json()["score"] is None
    finally:
        _cleanup_db(test_db)


def test_r7_client_error_rate_limiting():
    """R7: /api/client-error enforces sliding window rate limiting (10 req/60s) returning HTTP 429 without DB writes."""
    from webapp.routers.study import reset_client_error_rate_limits
    reset_client_error_rate_limits()

    test_db = BASE / "test_temp_api_r7.db"
    _cleanup_db(test_db)
    db.DB_FILE = test_db
    db.init_db()

    client = TestClient(server.app)
    try:
        # First 10 requests should succeed (HTTP 200)
        for i in range(10):
            r = client.post("/api/client-error", json={"message": f"error_{i}", "file": "app.js"})
            assert r.status_code == 200, f"Request {i+1} should succeed"

        # Verify exactly 10 error records in database
        conn = db.get_db()
        count = conn.execute("SELECT count(*) as c FROM error_logs WHERE level = 'UI_ERROR'").fetchone()["c"]
        assert count == 10

        # 11th request must return 429 Too Many Requests
        r11 = client.post("/api/client-error", json={"message": "flood_attempt", "file": "app.js"})
        assert r11.status_code == 429

        # 12th request must also return 429
        r12 = client.post("/api/client-error", json={"message": "flood_attempt_2", "file": "app.js"})
        assert r12.status_code == 429

        # Crucially: verify no additional rows were written to the database on 429
        count_after = conn.execute("SELECT count(*) as c FROM error_logs WHERE level = 'UI_ERROR'").fetchone()["c"]
        assert count_after == 10, "Rate-limited requests must not write to the error_logs table"

        # Reset rate limiter -> request allowed again
        reset_client_error_rate_limits()
        r_after_reset = client.post("/api/client-error", json={"message": "after_reset", "file": "app.js"})
        assert r_after_reset.status_code == 200
        count_final = conn.execute("SELECT count(*) as c FROM error_logs WHERE level = 'UI_ERROR'").fetchone()["c"]
        assert count_final == 11
    finally:
        reset_client_error_rate_limits()
        _cleanup_db(test_db)


def test_r8_webhook_timing_safe_secret(monkeypatch):
    """R8: /webhook verifies secret using secrets.compare_digest in constant time."""
    import secrets
    from webapp.routers import pwa

    client = TestClient(server.app)
    test_secret = "secure_webhook_secret_xyz_789"
    monkeypatch.setattr(pwa, "WEBHOOK_SECRET", test_secret)
    monkeypatch.setattr(pwa, "git_pull", lambda: "pull_mock_success")

    compare_digest_called = []
    orig_compare_digest = secrets.compare_digest

    def spy_compare_digest(a, b):
        compare_digest_called.append((a, b))
        return orig_compare_digest(a, b)

    monkeypatch.setattr(secrets, "compare_digest", spy_compare_digest)

    # 1. Missing secret -> 403 Forbidden
    r_no_sec = client.post("/webhook")
    assert r_no_sec.status_code == 403

    # 2. Wrong secret -> 403 Forbidden
    r_wrong = client.post("/webhook?secret=wrong_secret_value")
    assert r_wrong.status_code == 403

    # 3. Correct secret -> 200 OK
    r_correct = client.post(f"/webhook?secret={test_secret}")
    assert r_correct.status_code == 200
    assert "pull_mock_success" in r_correct.text

    # Verify secrets.compare_digest was called with the tested values
    assert len(compare_digest_called) >= 2
    assert any(call[0] == test_secret and call[1] == test_secret for call in compare_digest_called)


def test_glosar_and_automat_routes():
    import re
    import subprocess

    client = TestClient(server.app, headers={"User-Agent": "TestBrowser/1.0"})

    # 1. Zero-trust unauthenticated denial on pages, API, and exclusive assets
    for page in ("/automat", "/teorie", "/glosar"):
        r = client.get(page, follow_redirects=False)
        assert r.status_code in (302, 307)
        assert r.headers.get("location") == "/login"
    for ep in ("/api/teorie?source=_all", "/api/glosar?source=_all", "/fmt.js", "/automat-core.js", "/automat-delta.jpg"):
        assert client.get(ep).status_code == 401

    # 2. Tampered session cookie rejected
    bad_client = TestClient(server.app, headers={"User-Agent": "TestBrowser/1.0"})
    bad_client.cookies.set("tzi_session", "forged.token.value")
    assert bad_client.get("/api/teorie?source=_all").status_code == 401
    assert bad_client.get("/automat", follow_redirects=False).status_code in (302, 307)

    # 3. Trial login -> verify UA/IP session binding + strict headers + strict CSP
    assert client.get("/trial", follow_redirects=False).status_code in (302, 303, 307)
    cookie_val = client.cookies.get("tzi_session")
    assert cookie_val

    # Mismatched User-Agent with stolen cookie must fail (Zero-Trust fingerprint binding)
    thief = TestClient(server.app, headers={"User-Agent": "EvilScraper/9.9"})
    thief.cookies.set("tzi_session", cookie_val)
    assert thief.get("/api/teorie?source=_all").status_code == 401
    assert thief.get("/automat", follow_redirects=False).status_code in (302, 307)

    # Legitimate authenticated requests pass with strict CSP & security headers
    for page in ("/automat", "/teorie"):
        resp = client.get(page)
        assert resp.status_code == 200
        csp = resp.headers.get("content-security-policy", "")
        assert "default-src 'none'" in csp
        assert "script-src 'self'" in csp
        assert "'unsafe-inline'" not in csp
        assert "'wasm-unsafe-eval'" not in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("cross-origin-opener-policy") == "same-origin"
        assert resp.headers.get("cross-origin-resource-policy") == "same-origin"
        assert "no-store" in resp.headers.get("cache-control", "")
        # Zero inline <script>, <style>, style=, or on*= event handlers in HTML
        body = resp.text
        assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", body, re.I)
        assert not re.search(r"<style\b", body, re.I)
        assert not re.search(r"\bon\w+\s*=", body, re.I)
        assert "style=" not in body

    assert client.get("/fmt.js").status_code == 200
    assert client.get("/automat-core.js").status_code == 200
    assert client.get("/automat-delta.jpg").status_code == 200
    assert client.get("/static/css/automat.css").status_code == 200
    assert client.get("/static/js/automat.js").status_code == 200
    assert client.get("/static/css/glosar.css").status_code == 200
    assert client.get("/static/js/glosar.js").status_code == 200

    # 4. API input validation & no error-detail leak
    assert client.get("/api/glosar?source=../../etc/passwd").status_code == 400
    assert client.get("/api/glosar?source=%3Cscript%3E").status_code == 400
    r404 = client.get("/api/glosar?source=neexistujici_banka")
    assert r404.status_code == 404
    assert r404.json()["detail"] == "Zdroj nebyl nalezen"

    gl = client.get("/api/glosar?source=_all").json()
    assert len(gl["groups"]) >= 2
    srcs = [s["id"] for s in client.get("/api/sources").json()["sources"]]
    assert "06-2026-11-05" in srcs and "07-2026-11-12" in srcs

    # 5. Node.js check for fmt.js XSS escaping & ReDoS + automat-core.js prototype safety
    js_check = r"""
    const fs = require('fs');
    const vm = require('vm');
    const Auto = require('./ui/automat-core.js');
    const sp = Auto.parseSpec('Q = {__proto__, constructor, q0}\nΣ = {0}\npočáteční stav q0\nF = {}\nδ(q0, 0) = q0');
    if (sp.states.some(s => s.id === '__proto__' || s.id === 'constructor')) throw new Error('Reserved id allowed');
    const d = Auto.delta({ states: [{ id: 'q0' }], trans: [{ from: 'q0', to: 'q0', symbols: ['0'] }] });
    if (Object.getPrototypeOf(d) !== null || d.toString !== undefined) throw new Error('Prototype not null');

    const ctx = {};
    vm.runInNewContext(fs.readFileSync('./ui/fmt.js', 'utf8'), ctx);
    const xssOut = ctx.fmt('<img src=x onerror="alert(1)">\'test\'');
    if (xssOut.includes('<img') || xssOut.includes('"') || xssOut.includes("'")) throw new Error('fmt XSS leak: ' + xssOut);
    const t0 = Date.now();
    ctx.fmtZadani('G: a, pravidla ' + '(1) x '.repeat(50) + 'beztecky');
    if (Date.now() - t0 > 100) throw new Error('ReDoS detected');
    """
    res = subprocess.run(["node", "-e", js_check], cwd=str(BASE.parent), capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    for js_file in ("ui/js/automat.js", "ui/js/glosar.js", "ui/fmt.js", "ui/automat-core.js"):
        chk = subprocess.run(["node", "--check", js_file], cwd=str(BASE.parent), capture_output=True, text=True)
        assert chk.returncode == 0, f"{js_file}: {chk.stderr}"


def test_pentest_regressions():
    """Verify no premature XP grant, room detail IDOR, or browser-UA CSRF bypass."""
    test_db = BASE / "test_temp_pentest_reg.db"
    _cleanup_db(test_db)
    from webapp import questions
    db.DB_FILE = test_db
    db.init_db()
    questions.refresh_questions()

    try:
        c1 = TestClient(server.app, headers={"User-Agent": "Browser/1.0"})
        csrf1 = c1.get("/register").cookies.get("csrf_token")
        r1 = c1.post("/register", data={"username": "pt_u1", "password": "StrongPass123!", "password_confirm": "StrongPass123!", "csrf_token": csrf1}, follow_redirects=False)
        assert r1.status_code == 303
        csrf1 = c1.cookies.get("csrf_token")

        c2 = TestClient(server.app, headers={"User-Agent": "Browser/2.0"})
        csrf2 = c2.get("/register").cookies.get("csrf_token")
        r2 = c2.post("/register", data={"username": "pt_u2", "password": "StrongPass123!", "password_confirm": "StrongPass123!", "csrf_token": csrf2}, follow_redirects=False)
        assert r2.status_code == 303
        csrf2 = c2.cookies.get("csrf_token")

        qs = [q for q in c1.get("/api/questions?source=01-2026-10-01").json() if q.get("type") == "choice"]
        q0, q1 = qs[0], qs[1]

        # 1. Browser-UA POST /api/progress without X-CSRF-Token must fail 403
        assert c1.post("/api/progress?source=01-2026-10-01", json={"seen": {}, "latest": {"id": q0["id"], "userKeys": q0["correct"]}}).status_code == 403

        # 2. Forged match_token on /api/koth/submit must NOT award XP
        pts_before = c1.get("/api/me").json()["points"]
        assert c1.post("/api/koth/submit", json={"answers": [{"id": q0["id"], "userKeys": q0["correct"]}], "time_ms": 1, "match_token": "bad.token"}, headers={"X-CSRF-Token": csrf1}).status_code == 400
        assert c1.get("/api/me").json()["points"] == pts_before

        # 3. Room detail IDOR & non-member /api/rooms/{id}/submit must NOT leak questions or award XP
        room = c1.post("/api/rooms/create", json={"mode": "ffa", "name": "R", "count": 3, "source": "01-2026-10-01"}, headers={"X-CSRF-Token": csrf1}).json()["room"]
        assert c1.post(f"/api/rooms/{room['id']}/start", headers={"X-CSRF-Token": csrf1}).status_code == 200
        detail2 = c2.get(f"/api/rooms/{room['id']}").json()
        assert detail2["questions"] == []
        pts2_before = c2.get("/api/me").json()["points"]
        assert c2.post(f"/api/rooms/{room['id']}/submit", json={"answers": [{"id": q1["id"], "userKeys": q1["correct"]}], "time_ms": 1}, headers={"X-CSRF-Token": csrf2}).status_code == 403
        assert c2.get("/api/me").json()["points"] == pts2_before
    finally:
        _cleanup_db(test_db)


if __name__ == "__main__":
    import pytest
    test_full_pipeline()
    test_r2_progress_anti_spoofing()
    test_r7_client_error_rate_limiting()
    mp = pytest.MonkeyPatch()
    try:
        test_r8_webhook_timing_safe_secret(mp)
    finally:
        mp.undo()

