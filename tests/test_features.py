import subprocess
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

import inspect
import db
import scoring
import server
from webapp import questions


@pytest.fixture()
def temp_env(tmp_path):
    db.close_db()
    test_db = tmp_path / "test_features.db"
    old_db = db.DB_FILE
    db.DB_FILE = test_db
    db.init_db()
    client = TestClient(server.app)
    yield client
    db.close_db()
    db.DB_FILE = old_db


def test_r1_latex_katex_rendering():
    """R1: Ověření podpory LaTeXu (KaTeX) v ui/novy.html a neporušení běžného formátování."""
    novy_html = (BASE / "ui" / "novy.html").read_text(encoding="utf-8")
    assert "katex.min.css" in novy_html
    assert "katex.min.js" in novy_html

    node_check = r"""
    const fs = require('fs'), path = require('path'), vm = require('vm'), assert = require('assert');
    const html = fs.readFileSync('ui/novy.html', 'utf8');
    const scriptSrcs = [...html.matchAll(/<script src="([^"]+)"><\/script>/g)].map(m => m[1]).filter(s => s.startsWith('/static/js/'));
    const js = scriptSrcs.length > 0
      ? scriptSrcs.map(src => fs.readFileSync(path.join('ui', src.replace('/static/', '').split('?')[0]), 'utf8')).join('\n')
      : [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n');
    const ctx = vm.createContext({
      document: { getElementById: () => ({ style: {}, classList: { add(){}, remove(){} }, addEventListener(){} }), addEventListener(){}, querySelectorAll: () => [] },
      localStorage: { getItem: () => null, setItem(){} },
      fetch: () => new Promise(() => {}),
      setTimeout, setInterval, clearInterval,
      katex: {
        renderToString: (tex, opts) => `<span class="katex-rendered" data-display="${opts.displayMode}">${tex}</span>`
      }
    });
    vm.runInContext(js, ctx);
    const fmt = vm.runInContext('fmt', ctx);

    // 1. LaTeX vzorec nesmí mít rozbité podtržítko, stříšku ani nerovnost
    const outLatex = fmt('Platí $a_{n-1} + x^2 < y$ v posloupnosti.');
    assert(outLatex.includes('<span class="katex-rendered" data-display="false">a_{n-1} + x^2 < y</span>'), 'Chybné vykreslení inline LaTeXu: ' + outLatex);

    // 2. Display LaTeX $$...$$
    const outDisplay = fmt('Vzorec: $$\\sum_{i=1}^n i$$');
    assert(outDisplay.includes('<span class="katex-rendered" data-display="true">\\sum_{i=1}^n i</span>'), 'Chybné vykreslení display LaTeXu: ' + outDisplay);

    // 3. Běžný text bez LaTeXu si zachová dolní/horní indexy a šipky
    const outPlain = fmt('Posloupnost a_n -> Z^2');
    assert(outPlain.includes('a<sub>n</sub>') && outPlain.includes('→') && outPlain.includes('Z<sup>2</sup>'), 'Rozbité běžné formátování: ' + outPlain);

    // 4. Rozšířené auto-KaTeX vzorce a přísný CSP mathml režim bez inline style= na reálném KaTeXu
    const realKatex = require('./ui/vendor/katex/katex.min.js');
    for (const mode of ['', 'mathml']) {
      const mCtx = vm.createContext({
        katex: realKatex,
        document: { documentElement: { dataset: mode ? { katexMode: mode } : {} } }
      });
      vm.runInContext(fs.readFileSync('ui/js/format.js', 'utf8'), mCtx);
      const rFmt = vm.runInContext('fmt', mCtx);
      for (const expr of [
        'V_k(n) = n! / (n−k)!',
        '(n+k−1 nad k)',
        'Σ_(i=1)^n a_i',
        'Platí ℕ ⊂ ℤ ⊂ ℚ ⊂ ℝ ⊂ ℂ.',
        'Q = {zavřeno, otevřeno}, u ⇒^(∗) z, D_(f⁻¹) = H_f'
      ]) {
        const rendered = rFmt(expr);
        assert(rendered.includes('class="katex"'), 'Chybí KaTeX pro: ' + expr);
        assert(!rendered.includes('katex-error'), 'Chyba KaTeX pro: ' + expr);
        if (mode === 'mathml') {
          assert(!rendered.includes('style='), 'Zakázaný inline style= v mathml režimu: ' + expr);
        }
      }
    }
    """
    res = subprocess.run(["node", "-e", node_check], cwd=str(BASE), capture_output=True, text=True)
    assert res.returncode == 0, f"Node KaTeX test selhal: {res.stderr}\n{res.stdout}"


def test_r2_daily_minimal_progress_and_streak_reset(temp_env):
    """R2: Ověření denního minimálního postupu, inkrementace denního streaku a resetu při vynechání dne."""
    ok, err, user = db.register_user(theme="games", password="heslo123")
    assert ok and user is not None
    uid = user["id"]

    # Den 1: 2026-10-20 — 4 otázky (ještě pod cílem 5 otázek)
    for i in range(4):
        r = scoring.record_question_answer(uid, f"1-{i+1}", True, activity_date="2026-10-20")
        assert r["daily_goal_met"] is False
        assert r["daily_streak"] == 0

    # 5. otázka v Den 1 -> splní denní cíl, streak = 1
    r5 = scoring.record_question_answer(uid, "1-5", True, activity_date="2026-10-20")
    assert r5["daily_goal_met"] is True
    assert r5["daily_goal_just_met"] is True
    assert r5["daily_streak"] == 1

    # Den 2: 2026-10-21 (následující kalendářní den) -> splnění cíle zvýší streak na 2
    for i in range(scoring.DAILY_MIN_GOAL):
        r_d2 = scoring.record_question_answer(uid, f"2-{i+1}", True, activity_date="2026-10-21")
    assert r_d2["daily_goal_met"] is True
    assert r_d2["daily_streak"] == 2
    assert r_d2["best_daily_streak"] == 2

    # Den 3 (2026-10-22) je VYNECHÁN. Kontrola dne 2026-10-23 musí ukázat resetovaný denní streak = 0!
    dp_after_skip = scoring.get_daily_progress(uid, today_str="2026-10-23")
    assert dp_after_skip["daily_streak"] == 0
    assert dp_after_skip["best_daily_streak"] == 2
    assert dp_after_skip["goal_met"] is False

    # Splnění cíle 2026-10-23 nastaví nový streak na 1
    for i in range(scoring.DAILY_MIN_GOAL):
        r_d4 = scoring.record_question_answer(uid, f"3-{i+1}", True, activity_date="2026-10-23")
    assert r_d4["daily_streak"] == 1
    assert r_d4["best_daily_streak"] == 2


def test_r3_king_of_the_hill_1v1(temp_env):
    """R3: Ověření asynchronního kompetitivního režimu King of the Hill 1v1 a přebírání kopce."""
    client = temp_env

    # Zaregistrovat Hráče 1 a Hráče 2
    r1 = client.post("/register", data={"theme": "games", "password": "password1"}, follow_redirects=False)
    cookie1 = r1.cookies.get(server.SESSION_COOKIE)

    r2 = client.post("/register", data={"theme": "anime", "password": "password2"}, follow_redirects=False)
    cookie2 = r2.cookies.get(server.SESSION_COOKIE)

    # Hráč 1 spustí KotH a obsadí volný trůn
    client.cookies.set(server.SESSION_COOKIE, cookie1)
    me1 = client.get("/api/me").json()
    start_resp = client.post("/api/koth/start", json={"count": 5})
    assert start_resp.status_code == 200
    assert len(start_resp.json()["questions"]) > 0

    start1 = start_resp.json()
    token1 = start1["match_token"]
    qs1 = start1["questions"]

    def make_koth_answers(qs, correct_n):
        res = []
        for i, q in enumerate(qs):
            if i < correct_n:
                u_ans = list(q.get("correct", [])) if q.get("type", "choice") == "choice" else q.get("answer", "ok")
            else:
                u_ans = ["__wrong_ans__"]
            res.append({"id": q["id"], "userKeys": u_ans})
        return res

    sub1 = client.post("/api/koth/submit", json={
        "match_token": token1,
        "answers": make_koth_answers(qs1, 6),
        "time_ms": 30000
    })
    assert sub1.status_code == 200
    d1 = sub1.json()
    assert d1["won_throne"] is True
    assert d1["king"]["username"] == me1["username"]
    king1_score = d1["challenger_score"]

    # Hráč 2 zkusí vyzvat krále, ale získá nižší skóre -> Král 1 ubrání kopec
    client.cookies.set(server.SESSION_COOKIE, cookie2)
    me2 = client.get("/api/me").json()
    start2 = client.post("/api/koth/start").json()
    token2 = start2["match_token"]
    qs2 = start2["questions"]

    sub2_fail = client.post("/api/koth/submit", json={
        "match_token": token2,
        "answers": make_koth_answers(qs2, 3),
        "time_ms": 45000
    })
    assert sub2_fail.status_code == 200
    d2_fail = sub2_fail.json()
    assert d2_fail["won_throne"] is False
    assert d2_fail["king"]["username"] == me1["username"]
    assert d2_fail["king"]["defenses_count"] == 1

    # Hráč 2 dá lepší výsledek (9/10 rychle) -> sesadí Hráče 1 a stane se novým Králem kopce!
    start3 = client.post("/api/koth/start").json()
    token3 = start3["match_token"]
    qs3 = start3["questions"]

    sub2_win = client.post("/api/koth/submit", json={
        "match_token": token3,
        "answers": make_koth_answers(qs3, 9),
        "time_ms": 15000
    })
    assert sub2_win.status_code == 200
    d2_win = sub2_win.json()
    assert d2_win["won_throne"] is True
    assert d2_win["challenger_score"] > king1_score
    assert d2_win["king"]["username"] == me2["username"]
    assert d2_win["king"]["defenses_count"] == 0

    # Ověření přes GET /api/koth/status
    st = client.get("/api/koth/status").json()
    assert st["king"]["username"] == me2["username"]
    assert len(st["recent_matches"]) == 3


def test_r4_open_registration_and_relogin_without_invite(temp_env):
    """R4: Ověření registrace bez pozvánkového kódu a následného přihlášení."""
    client = temp_env

    reg_page = client.get("/register")
    assert reg_page.status_code == 200
    assert 'name="invite_code"' not in reg_page.text

    csrf_token = reg_page.cookies.get("csrf_token")
    reg_res = client.post("/register", data={"theme": "series", "password": "super_secret_pw", "csrf_token": csrf_token}, follow_redirects=False)
    assert reg_res.status_code == 303
    session_cookie = reg_res.cookies.get(server.SESSION_COOKIE)
    assert session_cookie is not None

    client.cookies.set(server.SESSION_COOKIE, session_cookie)
    me = client.get("/api/me").json()
    assigned_username = me["username"]
    assert assigned_username and me["theme"] == "series"

    # Odhlášení a opětovné přihlášení přes /login
    client.get("/logout")
    client.cookies.clear()

    login_res = client.post("/login", data={"username": assigned_username, "password": "super_secret_pw"}, follow_redirects=False)
    assert login_res.status_code == 303
    new_cookie = login_res.cookies.get(server.SESSION_COOKIE)
    assert new_cookie is not None

    client.cookies.set(server.SESSION_COOKIE, new_cookie)
    me_again = client.get("/api/me").json()
    assert me_again["username"] == assigned_username


def test_r5_wasm_binary_and_client_logic(temp_env):
    """R5: Ověření WebAssembly modulu (zdrojový kód, sestavená binárka, HTTP endpoint a běh v JS/WASM)."""
    client = temp_env
    wasm_src = BASE / "wasm" / "quiz_core.ts"
    wasm_bin = BASE / "ui" / "quiz.wasm"
    build_script = (BASE / "scripts" / "build_wasm.py") if (BASE / "scripts" / "build_wasm.py").exists() else (BASE / "build_wasm.py")

    assert wasm_src.exists(), "Chybí zdrojový kód WASM modulu"
    assert wasm_bin.exists(), "Chybí zkompilovaný ui/quiz.wasm"
    assert build_script.exists(), "Chybí sestavovací skript build_wasm.py"

    # Ověřit HTTP servírování /quiz.wasm
    resp = client.get("/quiz.wasm")
    assert resp.status_code == 200
    assert resp.content[:4] == b"\x00asm"

    # Spustit kompletní klientský test test_doplnovacka.js běžící nad WASM jádrem
    js_path = str(BASE / "tests" / "test_doplnovacka.js") if (BASE / "tests" / "test_doplnovacka.js").exists() else "test_doplnovacka.js"
    proc = subprocess.run(["node", js_path], cwd=str(BASE), capture_output=True, text=True)
    assert proc.returncode == 0, f"test_doplnovacka.js selhal:\n{proc.stdout}\n{proc.stderr}"
    assert "chyb: 0" in proc.stdout


def test_r6_all_competitive_modes_and_classic_registration(temp_env):
    """R6: Ověření všech kompetitivních režimů (FFA, 1v1 Duel, KotH), klasické registrace se jménem a odstranění starého vzhledu."""
    client = temp_env

    # 1. Starý vzhled (klasicky.html) je pryč
    assert not (BASE / "ui" / "klasicky.html").exists()
    novy_html = (BASE / "ui" / "novy.html").read_text(encoding="utf-8")
    assert "Starý vzhled" not in novy_html
    assert "startCompetitiveMode('ffa')" in novy_html
    assert "startCompetitiveMode('duel')" in novy_html
    assert "startKothChallenge()" in novy_html

    # 2. Klasická registrace s vlastním uživatelským jménem a potvrzením hesla
    r1 = client.post("/register", data={
        "username": "Alchymista_CZ",
        "password": "password123",
        "password_confirm": "password123"
    }, follow_redirects=False)
    assert r1.status_code == 303
    c1 = r1.cookies.get(server.SESSION_COOKIE)

    r2 = client.post("/register", data={
        "username": "Rytir_CZ",
        "password": "password456",
        "password_confirm": "password456"
    }, follow_redirects=False)
    assert r2.status_code == 303
    c2 = r2.cookies.get(server.SESSION_COOKIE)

    # 3. Free For All (FFA)
    client.cookies.set(server.SESSION_COOKIE, c1)
    ffa_start = client.post("/api/ffa/start", json={"count": 5})
    assert ffa_start.status_code == 200
    assert ffa_start.json()["mode"] == "ffa"
    def make_ffa_answers(qs, correct_n):
        res = []
        for i, q in enumerate(qs):
            if i < correct_n:
                u_ans = list(q.get("correct", [])) if q.get("type", "choice") == "choice" else q.get("answer", "ok")
            else:
                u_ans = ["__wrong_ans__"]
            res.append({"id": q["id"], "userKeys": u_ans})
        return res

    start_ffa1 = client.post("/api/ffa/start").json()
    ffa_sub1 = client.post("/api/ffa/submit", json={
        "match_token": start_ffa1["match_token"],
        "answers": make_ffa_answers(start_ffa1["questions"], 7),
        "time_ms": 20000
    }).json()
    assert ffa_sub1["rank"] == 1 and ffa_sub1["is_leader"] is True

    client.cookies.set(server.SESSION_COOKIE, c2)
    start_ffa2 = client.post("/api/ffa/start").json()
    ffa_sub2 = client.post("/api/ffa/submit", json={
        "match_token": start_ffa2["match_token"],
        "answers": make_ffa_answers(start_ffa2["questions"], 9),
        "time_ms": 18000
    }).json()
    assert ffa_sub2["rank"] == 1 and ffa_sub2["is_leader"] is True

    # 4. 1v1 Duel (Hráč 1 založí výzvu, Hráč 2 ji přijme a vyhraje)
    client.cookies.set(server.SESSION_COOKIE, c1)
    duel_start1 = client.post("/api/duel/start", json={"count": 5}).json()
    def make_duel_answers(qs, correct_n):
        res = []
        for i, q in enumerate(qs):
            if i < correct_n:
                u_ans = list(q.get("correct", [])) if q.get("type", "choice") == "choice" else q.get("answer", "ok")
            else:
                u_ans = ["__wrong_ans__"]
            res.append({"id": q["id"], "userKeys": u_ans})
        return res

    duel_sub1 = client.post("/api/duel/submit", json={
        "match_token": duel_start1["match_token"],
        "answers": make_duel_answers(duel_start1["questions"], 3),
        "time_ms": 40000,
    }).json()
    assert duel_sub1["resolved"] is False
    duel_id = duel_sub1["duel_id"]

    client.cookies.set(server.SESSION_COOKIE, c2)
    duel_start2 = client.post("/api/duel/start", json={"duel_id": duel_id}).json()
    assert duel_start2["duel"]["id"] == duel_id
    duel_sub2 = client.post("/api/duel/submit", json={
        "match_token": duel_start2["match_token"],
        "duel_id": duel_id,
        "answers": make_duel_answers(duel_start2["questions"], 5),
        "time_ms": 15000,
    }).json()
    assert duel_sub2["resolved"] is True
    assert duel_sub2["won_duel"] is True
    assert duel_sub2["winner_username"] == "Rytir_CZ"

    # 5. Souhrnný endpoint /api/competitive/overview
    ov = client.get("/api/competitive/overview").json()
    assert "ffa" in ov and "duel" in ov and "koth" in ov
    assert ov["ffa"]["leader"]["username"] == "Rytir_CZ"
    assert len(ov["duel"]["recent_duels"]) == 1


def test_r7_competitive_rooms_lobby_and_host_start(temp_env):
    """R7: Ověření kompetitivních místností (Rooms v lobby) – vytvoření, čekání na hráče, spuštění 👑 hostitelem i auto-start 1v1."""
    client = temp_env

    # Zaregistrovat 2 hráče
    r1 = client.post("/register", data={"username": "HostKing", "password": "pw123456", "password_confirm": "pw123456"}, follow_redirects=False)
    c1 = r1.cookies.get(server.SESSION_COOKIE)
    r2 = client.post("/register", data={"username": "ChallengerTwo", "password": "pw123456", "password_confirm": "pw123456"}, follow_redirects=False)
    c2 = r2.cookies.get(server.SESSION_COOKIE)

    # 1. HostKing vytvoří FFA místnost
    client.cookies.set(server.SESSION_COOKIE, c1)
    cr = client.post("/api/rooms/create", json={"mode": "ffa", "name": "Večerní TZI Aréna", "count": 5}).json()
    assert cr["ok"] is True
    room_id = cr["room"]["id"]
    assert cr["room"]["status"] == "waiting"
    assert cr["room"]["host_username"] == "HostKing"
    assert cr["room"]["player_count"] == 1

    # 2. ChallengerTwo vidí místnost v lobby a připojí se
    client.cookies.set(server.SESSION_COOKIE, c2)
    rooms_list = client.get("/api/rooms").json()
    assert any(r["id"] == room_id for r in rooms_list["active_rooms"])

    join_res = client.post(f"/api/rooms/{room_id}/join", json={"auto_start_duel": False}).json()
    assert join_res["ok"] is True
    assert join_res["room"]["player_count"] == 2
    assert join_res["room"]["status"] == "waiting"

    # ChallengerTwo (není 👑 host) nemůže hru odstartovat
    bad_start = client.post(f"/api/rooms/{room_id}/start")
    assert bad_start.status_code == 403

    # 3. HostKing (👑) odstartuje místnost
    client.cookies.set(server.SESSION_COOKIE, c1)
    start_res = client.post(f"/api/rooms/{room_id}/start")
    assert start_res.status_code == 200
    started_data = start_res.json()
    assert started_data["room"]["status"] == "in_progress"
    assert len(started_data["questions"]) == 5
    room_qs = started_data["questions"]

    def make_room_answers(qs, correct_n):
        res = []
        for i, q in enumerate(qs):
            if i < correct_n:
                u_ans = list(q.get("correct", [])) if q.get("type", "choice") == "choice" else q.get("answer", "ok")
            else:
                u_ans = ["__wrong_ans__"]
            res.append({"id": q["id"], "userKeys": u_ans})
        return res

    # 4. Oba hráči odešlou výsledky v místnosti
    sub1 = client.post(f"/api/rooms/{room_id}/submit", json={
        "answers": make_room_answers(room_qs, 3),
        "time_ms": 25000
    }).json()
    assert sub1["ok"] is True
    assert sub1["room"]["status"] == "in_progress"  # Čeká na druhého hráče

    client.cookies.set(server.SESSION_COOKIE, c2)
    sub2 = client.post(f"/api/rooms/{room_id}/submit", json={
        "answers": make_room_answers(room_qs, 5),
        "time_ms": 15000
    }).json()
    assert sub2["ok"] is True
    assert sub2["room"]["status"] == "completed"
    assert sub2["room"]["winner_username"] == "ChallengerTwo"
    assert sub2["rank"] == 1

    # 5. Test 1v1 Duel místnosti s auto-startem po připojení 2. hráče
    client.cookies.set(server.SESSION_COOKIE, c1)
    duel_room = client.post("/api/rooms/create", json={"mode": "duel", "name": "Rychlé 1v1", "count": 5}).json()["room"]
    assert duel_room["status"] == "waiting" and duel_room["max_players"] == 2

    client.cookies.set(server.SESSION_COOKIE, c2)
    duel_join = client.post(f"/api/rooms/{duel_room['id']}/join", json={"auto_start_duel": True}).json()
    assert duel_join["room"]["status"] == "in_progress"
    assert len(duel_join["questions"]) == 5


def test_r8_profile_recap_leaderboard_and_revalidation(temp_env):
    """R8: Ověření subpage Kompetitivní aréna, Profil + Recap, Žebříček a revalidace při mazání dat."""
    client = temp_env
    novy_html = (BASE / "ui" / "novy.html").read_text(encoding="utf-8")
    assert 'id="comp-arena"' in novy_html
    assert 'id="profile-view"' in novy_html
    assert 'id="leaderboard-view"' in novy_html
    assert 'id="revalidate-modal"' in novy_html
    full_ui_bundle = novy_html + "".join(f.read_text(encoding="utf-8") for f in sorted((BASE / "ui" / "js").glob("*.js")))
    assert "WASM_CORE.exp.calcAchievementMask" in full_ui_bundle
    assert "WASM_CORE.exp.calcRecapAccuracy" in full_ui_bundle

    r = client.post("/register", data={"username": "StudentRecap", "password": "secret123", "password_confirm": "secret123"}, follow_redirects=False)
    assert r.status_code == 303
    client.cookies.set(server.SESSION_COOKIE, r.cookies.get(server.SESSION_COOKIE))

    # Recap endpoint
    recap = client.get("/api/account/recap").json()
    assert recap["username"] == "StudentRecap"
    assert isinstance(recap["sources"], list) and len(recap["sources"]) > 0

    # Leaderboard endpoint s plným žebříčkem
    lb = client.get("/api/leaderboard").json()
    assert "leaderboard" in lb and isinstance(lb["leaderboard"], list)

    # Revalidace před smazáním dat - špatné heslo musí vrátit 403
    bad_del = client.post("/api/account/revalidate-delete", json={"password": "wrongpassword", "scope": "source", "source": "01-2026-10-01"})
    assert bad_del.status_code == 403

    # Revalidace se správným heslem projde
    ok_del = client.post("/api/account/revalidate-delete", json={"password": "secret123", "scope": "source", "source": "01-2026-10-01"})
    assert ok_del.status_code == 200 and ok_del.json()["ok"] is True

    # Změna přezdívky
    u_res = client.post("/api/account/username", json={"username": "StudentMaster"})
    assert u_res.status_code == 200 and u_res.json()["username"] == "StudentMaster"


def test_r9_delete_profile_removes_account(temp_env):
    """R9: Smazání profilu (delete-profile) odstraní uživatele i jeho odpovědi; špatné heslo vrátí 403."""
    client = temp_env
    r = client.post("/register", data={"username": "test123", "password": "heslo1234", "password_confirm": "heslo1234"}, follow_redirects=False)
    assert r.status_code == 303
    client.cookies.set(server.SESSION_COOKIE, r.cookies.get(server.SESSION_COOKIE))
    uid = db.authenticate_user("test123", "heslo1234")["id"]
    scoring.record_question_answer(uid, "1-1", True)

    payload = {"step1_ack": True, "confirm_username": "test123", "confirm_phrase": "DELETE", "password": "spatne"}
    assert client.post("/api/account/delete-profile", json=payload).status_code == 403

    payload["password"] = "heslo1234"
    res = client.post("/api/account/delete-profile", json=payload)
    assert res.status_code == 200 and res.json()["ok"] is True

    conn = db.get_db()
    assert conn.execute("SELECT COUNT(*) FROM users WHERE id = ?", (uid,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM user_answers WHERE user_id = ?", (uid,)).fetchone()[0] == 0
    assert db.authenticate_user("test123", "heslo1234") is None


def test_r10_html_templates_escape_user_input(temp_env):
    """R10: login/register/admin šablony escapují text z URL i uživatelská jména (ochrana proti XSS)."""
    client = temp_env
    payload = "<script>alert(1)</script>"

    for url in (f"/login?error={payload}", f"/login?success={payload}", f"/register?error={payload}"):
        page = client.get(url).text
        assert payload not in page, url
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page, url

    ok, err, user = db.register_user(theme="games", password="heslo1234")
    assert ok and user is not None
    evil_name = "<img src=x onerror=alert(2)>"
    conn = db.get_db()
    with conn:
        conn.execute("UPDATE users SET username = ? WHERE id = ?", (evil_name, user["id"]))
    scoring.record_question_answer(user["id"], "1-1", True)

    admin_token = server.create_session_token({"id": 1, "username": "Admin", "role": "admin", "theme": "games"})
    client.cookies.set(server.SESSION_COOKIE, admin_token)
    admin_page = client.get(f"/admin?new_code={payload}").text
    assert evil_name not in admin_page
    assert payload not in admin_page
    assert "&lt;img src=x onerror=alert(2)&gt;" in admin_page


def test_r3_koth_exploit_prevention(temp_env):
    """R3: Ověření eliminace KotH exploitů - povinné answers pole, zákaz correct_count a client isCorrect."""
    client = temp_env
    r = client.post("/register", data={"theme": "games", "password": "password123"}, follow_redirects=False)
    cookie = r.cookies.get(server.SESSION_COOKIE)
    client.cookies.set(server.SESSION_COOKIE, cookie)

    # 1. Chybějící pole answers -> HTTP 400
    res_no_ans = client.post("/api/koth/submit", json={"correct_count": 5, "total_questions": 5, "time_ms": 10000})
    assert res_no_ans.status_code == 400
    assert "Pole answers je povinné." in res_no_ans.json()["detail"]

    # 2. Prázdné pole answers -> HTTP 400
    res_empty_ans = client.post("/api/koth/submit", json={"answers": [], "time_ms": 10000})
    assert res_empty_ans.status_code == 400
    assert "Pole answers je povinné." in res_empty_ans.json()["detail"]

    # 3. Pokus o podvrh isCorrect bez uživatelské odpovědi -> vyhodnoceno jako 0 bodů
    q_start = client.post("/api/koth/start").json()
    token = q_start["match_token"]
    q = q_start["questions"][0]

    res_spoof = client.post("/api/koth/submit", json={
        "match_token": token,
        "answers": [{"id": q["id"], "isCorrect": True}],
        "time_ms": 10000
    })
    assert res_spoof.status_code == 200
    assert res_spoof.json()["challenger_score"] == 0

    # 4. Skutečně správná odpověď s novým platným match_tokenem -> server-side ověřeno a uděleno skóre
    q_start2 = client.post("/api/koth/start").json()
    token2 = q_start2["match_token"]
    q2 = q_start2["questions"][0]
    u_ans = list(q2.get("correct", [])) if q2.get("type", "choice") == "choice" else q2.get("answer", "ok")
    res_valid = client.post("/api/koth/submit", json={
        "match_token": token2,
        "answers": [{"id": q2["id"], "userKeys": u_ans}],
        "time_ms": 10000
    })
    assert res_valid.status_code == 200
    assert res_valid.json()["challenger_score"] > 0
    assert res_valid.json()["won_throne"] is True


def test_r4_multiplayer_score_spoofing_prevention(temp_env):
    """R4: Ověření odstranění explicit_score ze scoring/rooms.py i webapp/routers/competitive.py."""
    client = temp_env
    # 1. Ověření signatury funkce scoring.submit_comp_room_result
    sig = inspect.signature(scoring.submit_comp_room_result)
    assert "explicit_score" not in sig.parameters

    # 2. Registrace uživatele a vytvoření místnosti
    r = client.post("/register", data={"theme": "fantasy", "password": "password123"}, follow_redirects=False)
    cookie = r.cookies.get(server.SESSION_COOKIE)
    client.cookies.set(server.SESSION_COOKIE, cookie)

    room_data = client.post("/api/rooms/create", json={"mode": "ffa", "name": "Anti-Cheat Room", "count": 5}).json()["room"]
    room_id = room_data["id"]
    client.post(f"/api/rooms/{room_id}/start")

    # 3. Pokus o odeslání podvrženého explicitního skóre (score: 999999)
    q_id = room_data["question_ids"][0] if room_data.get("question_ids") else list(questions.ALL_QUESTIONS.keys())[0]
    res = client.post(f"/api/rooms/{room_id}/submit", json={
        "score": 999999,
        "answers": [{"id": q_id, "userKeys": ["__wrong_ans__"]}],
        "time_ms": 1000
    })
    assert res.status_code == 200
    # Server musí spočítat skóre sám (při 0 správných je speed_bonus 0 -> skóre 0)
    assert res.json()["score"] == 0
    assert res.json()["score"] < 999999

    # 4. Ověření odmítnutí chybějícího answers / podvrženého correct_count
    res_no_ans = client.post(f"/api/rooms/{room_id}/submit", json={"correct_count": 5, "time_ms": 1000})
    assert res_no_ans.status_code == 400
    assert "Pole answers je povinné." in res_no_ans.json()["detail"]


def test_r5_self_duel_prevention(temp_env):
    """R5: Zákaz self-duel farming v /api/duel/start."""
    client = temp_env
    r = client.post("/register", data={"theme": "scifi", "password": "password123"}, follow_redirects=False)
    cookie = r.cookies.get(server.SESSION_COOKIE)
    client.cookies.set(server.SESSION_COOKIE, cookie)
    me = client.get("/api/me").json()
    uid = me["user_id"]

    # 1. Přímá výzva sama sebe přes opponent_id -> HTTP 400
    res_self = client.post("/api/duel/start", json={"opponent_id": uid})
    assert res_self.status_code == 400
    assert res_self.json()["detail"] == "Nelze vyzvat sám sebe."

    # Non-integer opponent_id -> HTTP 400
    res_non_int_opp = client.post("/api/duel/start", json={"opponent_id": "invalid_id"})
    assert res_non_int_opp.status_code == 400
    assert "Neplatné opponent_id." in res_non_int_opp.json()["detail"]

    # Non-integer duel_id in /api/duel/start -> HTTP 400
    res_non_int_duel = client.post("/api/duel/start", json={"duel_id": "invalid_duel"})
    assert res_non_int_duel.status_code == 400
    assert "Neplatné duel_id." in res_non_int_duel.json()["detail"]

    # 2. Založení otevřeného duelu
    d_start = client.post("/api/duel/start", json={"count": 5}).json()
    token = d_start["match_token"]
    q = d_start["questions"][0]
    u_ans = list(q.get("correct", [])) if q.get("type", "choice") == "choice" else q.get("answer", "ok")

    # Rejection of missing answers / spoofed correct_count in /api/duel/submit -> HTTP 400
    res_spoof_duel = client.post("/api/duel/submit", json={"match_token": token, "correct_count": 5, "time_ms": 10000})
    assert res_spoof_duel.status_code == 400
    assert "Pole answers je povinné." in res_spoof_duel.json()["detail"]

    # Non-integer duel_id in /api/duel/submit -> HTTP 400
    res_sub_bad_duel = client.post("/api/duel/submit", json={
        "match_token": token,
        "duel_id": "invalid_duel",
        "answers": [{"id": q["id"], "userKeys": u_ans}],
        "time_ms": 10000
    })
    assert res_sub_bad_duel.status_code == 400
    assert "Neplatné duel_id." in res_sub_bad_duel.json()["detail"]

    # Non-integer time_ms in /api/duel/submit -> HTTP 400
    res_sub_bad_time = client.post("/api/duel/submit", json={
        "match_token": token,
        "answers": [{"id": q["id"], "userKeys": u_ans}],
        "time_ms": "not_a_time"
    })
    assert res_sub_bad_time.status_code == 400
    assert "Neplatný čas (time_ms)." in res_sub_bad_time.json()["detail"]

    sub_res = client.post("/api/duel/submit", json={
        "match_token": token,
        "answers": [{"id": q["id"], "userKeys": u_ans}],
        "time_ms": 10000
    }).json()
    duel_id = sub_res["duel_id"]

    # 3. Pokus připojit se do vlastního duelu přes duel_id -> HTTP 400
    res_join_own = client.post("/api/duel/start", json={"duel_id": duel_id})
    assert res_join_own.status_code == 400
    assert res_join_own.json()["detail"] == "Nelze vyzvat sám sebe."


def test_r6_ffa_time_and_answer_validation(temp_env):
    """R6: Anti-speedhack a validace answers v /api/ffa/submit."""
    client = temp_env
    r = client.post("/register", data={"theme": "nature", "password": "password123"}, follow_redirects=False)
    cookie = r.cookies.get(server.SESSION_COOKIE)
    client.cookies.set(server.SESSION_COOKIE, cookie)

    start_ffa = client.post("/api/ffa/start").json()
    token = start_ffa["match_token"]
    q = start_ffa["questions"][0]
    u_ans = list(q.get("correct", [])) if q.get("type", "choice") == "choice" else q.get("answer", "ok")
    valid_answers = [{"id": q["id"], "userKeys": u_ans}]

    # 1. Chybějící pole answers (pouze correct_count) -> HTTP 400
    res_no_ans = client.post("/api/ffa/submit", json={"match_token": token, "correct_count": 5, "time_ms": 10000})
    assert res_no_ans.status_code == 400
    assert "Pole answers je povinné." in res_no_ans.json()["detail"]

    # 2. Prázdné pole answers -> HTTP 400
    res_empty_ans = client.post("/api/ffa/submit", json={"match_token": token, "answers": [], "time_ms": 10000})
    assert res_empty_ans.status_code == 400
    assert "Pole answers je povinné." in res_empty_ans.json()["detail"]

    # 3. Nerealistický čas (< 5000 ms) -> HTTP 400
    res_speedhack = client.post("/api/ffa/submit", json={"match_token": token, "answers": valid_answers, "time_ms": 4999})
    assert res_speedhack.status_code == 400
    assert "Čas dokončení je příliš krátký (minimálně 5 sekund)." in res_speedhack.json()["detail"]

    # 4. Nulový čas -> HTTP 400
    res_zero = client.post("/api/ffa/submit", json={"match_token": token, "answers": valid_answers, "time_ms": 0})
    assert res_zero.status_code == 400

    # 5. Hraniční platný čas (5000 ms) -> HTTP 200 (s novým tokenem a otázkami pro odevzdání)
    st5 = client.post("/api/ffa/start").json()
    t5 = st5["match_token"]
    q5 = st5["questions"][0]
    u_ans5 = list(q5.get("correct", [])) if q5.get("type", "choice") == "choice" else q5.get("answer", "ok")
    res_boundary = client.post("/api/ffa/submit", json={"match_token": t5, "answers": [{"id": q5["id"], "userKeys": u_ans5}], "time_ms": 5000})
    assert res_boundary.status_code == 200
    assert res_boundary.json()["score"] > 0

    # 6. Podvrh isCorrect bez uživatelské odpovědi -> 0 bodů
    st6 = client.post("/api/ffa/start").json()
    t6 = st6["match_token"]
    q6 = st6["questions"][0]
    res_spoof = client.post("/api/ffa/submit", json={
        "match_token": t6,
        "answers": [{"id": q6["id"], "isCorrect": True}],
        "time_ms": 6000
    })
    assert res_spoof.status_code == 200
    assert res_spoof.json()["score"] == 0

    # 7. Neplatný čas (nečíselný) -> HTTP 400
    st7 = client.post("/api/ffa/start").json()
    t7 = st7["match_token"]
    q7 = st7["questions"][0]
    u_ans7 = list(q7.get("correct", [])) if q7.get("type", "choice") == "choice" else q7.get("answer", "ok")
    res_bad_time = client.post("/api/ffa/submit", json={"match_token": t7, "answers": [{"id": q7["id"], "userKeys": u_ans7}], "time_ms": "invalid"})
    assert res_bad_time.status_code == 400
    assert "Neplatný čas (time_ms)." in res_bad_time.json()["detail"]


def test_admin_auth_security_no_bypass(temp_env):
    """Admin účet nelze obejít libovolným heslem a funguje zadané heslo."""
    client = temp_env
    r = client.post("/login", data={"username": "admin", "password": "cokoliv123"}, follow_redirects=False)
    assert r.status_code == 303
    assert "error=" in r.headers["location"]
    assert server.SESSION_COOKIE not in r.cookies

    # Inicializovat admina s výchozím / novým hashem
    from webapp.config import HASHED_PASSWORD
    db.ensure_admin_exists(HASHED_PASSWORD)

    r_bad = client.post("/login", data={"username": "admin", "password": "wrong_password"}, follow_redirects=False)
    assert r_bad.status_code == 303
    assert "error=" in r_bad.headers["location"]
    assert server.SESSION_COOKIE not in r_bad.cookies

    r_ok = client.post("/login", data={"username": "admin", "password": "3f%x#T0hl8uqv$lyKI9p%55%"}, follow_redirects=False)
    assert r_ok.status_code == 303
    assert r_ok.headers["location"] == "/"
    assert server.SESSION_COOKIE in r_ok.cookies


def test_csrf_double_submit_and_api_me(temp_env):
    """CSRF token je v /api/me i v cookie, a /api/account/username ověřuje X-CSRF-Token."""
    client = temp_env
    r = client.post("/register", data={"username": "CsrfUser", "password": "secret_password123", "password_confirm": "secret_password123"}, follow_redirects=False)
    client.cookies.set(server.SESSION_COOKIE, r.cookies.get(server.SESSION_COOKIE))

    me_res = client.get("/api/me")
    assert me_res.status_code == 200
    data = me_res.json()
    assert "csrf_token" in data and len(data["csrf_token"]) == 64
    csrf_token = data["csrf_token"]

    assert client.cookies.get("csrf_token") == csrf_token

    bad_res = client.post("/api/account/username", json={"username": "HackedNick"}, headers={"X-CSRF-Token": "invalid_csrf_token_value"})
    assert bad_res.status_code == 403
    assert bad_res.json()["detail"] == "Neplatný CSRF token."

    good_res = client.post("/api/account/username", json={"username": "ValidNick"}, headers={"X-CSRF-Token": csrf_token})
    assert good_res.status_code == 200
    assert good_res.json()["username"] == "ValidNick"


def test_repeated_question_streak_farm_prevention(temp_env):
    """Zákaz farmení XP opakovaným posíláním téže otázky (streak bonus i body = 0)."""
    client = temp_env
    r = client.post("/register", data={"username": "FarmTester", "password": "password123", "password_confirm": "password123"}, follow_redirects=False)
    client.cookies.set(server.SESSION_COOKIE, r.cookies.get(server.SESSION_COOKIE))
    me = client.get("/api/me").json()
    uid = me["user_id"]

    # 1. První odpověď získá standardní body (3 body)
    r1 = scoring.record_question_answer(uid, "1-1", True)
    assert r1["points_awarded"] == 3
    assert r1["streak"] == 1

    # 2. Opakování téže otázky 20x nesmí přidělit žádné další body ani streak bonus
    for _ in range(20):
        r_repeat = scoring.record_question_answer(uid, "1-1", True)
        assert r_repeat["points_awarded"] == 0
        assert r_repeat["streak_bonus"] == 0
        assert r_repeat["streak"] == 1

    # Celkové body v profilu musí zůstat 3, ne 40+
    me_after = client.get("/api/me").json()
    assert me_after["points"] == 3
    assert me_after["streak"] == 1


def test_room_security_enforcement(temp_env):
    """Místnost vyžaduje stav in_progress, členství hráče a odmítá cizí otázky."""
    client = temp_env
    r1 = client.post("/register", data={"username": "HostPlayer", "password": "password123", "password_confirm": "password123"}, follow_redirects=False)
    cookie_host = r1.cookies.get(server.SESSION_COOKIE)

    r2 = client.post("/register", data={"username": "OutsiderPlayer", "password": "password123", "password_confirm": "password123"}, follow_redirects=False)
    cookie_outsider = r2.cookies.get(server.SESSION_COOKIE)

    # Host vytvoří místnost
    client.cookies.set(server.SESSION_COOKIE, cookie_host)
    c_res = client.post("/api/rooms/create", json={"mode": "ffa", "name": "SecureRoom", "count": 5}).json()
    room_id = c_res["room"]["id"]
    room_qids = c_res["room"]["question_ids"]

    # 1. Odeslání do místnosti před jejím zahájením (/start) -> 400
    res_not_started = client.post(f"/api/rooms/{room_id}/submit", json={"answers": [{"id": room_qids[0], "userKeys": ["A"]}], "time_ms": 5000})
    assert res_not_started.status_code == 400
    assert "in_progress" in res_not_started.json()["detail"]

    # 2. Host spustí místnost
    client.post(f"/api/rooms/{room_id}/start")

    # 3. Outsider (nepřipojený hráč) se pokusí odeslat výsledek -> 403
    client.cookies.set(server.SESSION_COOKIE, cookie_outsider)
    res_outsider = client.post(f"/api/rooms/{room_id}/submit", json={"answers": [{"id": room_qids[0], "userKeys": ["A"]}], "time_ms": 5000})
    assert res_outsider.status_code == 403
    assert "Nejste hráčem" in res_outsider.json()["detail"]

    # 4. Host pošle cizí otázky, které nepatří do místnosti -> 400
    client.cookies.set(server.SESSION_COOKIE, cookie_host)
    res_alien = client.post(f"/api/rooms/{room_id}/submit", json={"answers": [{"id": "99-99-alien", "userKeys": ["A"]}], "time_ms": 5000})
    assert res_alien.status_code == 400
    assert "nepatří do této místnosti" in res_alien.json()["detail"]


def test_admin_leaderboard_management_and_removal(temp_env):
    """Admin může odebrat studenta ze žebříčku, vrátit ho a resetovat mu body."""
    client = temp_env
    # 1. Zaregistrovat studenta a nahrát mu body
    r = client.post("/register", data={"username": "CheaterX", "password": "password123", "password_confirm": "password123"}, follow_redirects=False)
    cookie_user = r.cookies.get(server.SESSION_COOKIE)
    client.cookies.set(server.SESSION_COOKIE, cookie_user)
    me = client.get("/api/me").json()
    uid = me["user_id"]
    scoring.record_question_answer(uid, "1-1", True)

    # Uživatel je v žebříčku
    lb_before = client.get("/api/leaderboard").json()
    assert any(u["username"] == "CheaterX" for u in lb_before["leaderboard"])

    # 2. Přihlásit se jako admin
    admin_token = server.create_session_token({"id": 1, "username": "Admin", "role": "admin", "theme": "games"})
    client.cookies.set(server.SESSION_COOKIE, admin_token)

    # Admin vidí studenta v tabulce s tlačítkem 'Odebrat z žebříčku'
    admin_page = client.get("/admin").text
    assert "CheaterX" in admin_page
    assert "Odebrat z žebříčku" in admin_page
    csrf_token = client.cookies.get("csrf_token")

    # 3. Admin odebere studenta ze žebříčku
    res_toggle = client.post("/admin/leaderboard/toggle", data={"user_id": uid, "csrf_token": csrf_token}, follow_redirects=False)
    assert res_toggle.status_code == 303

    # V admin panelu je nyní označen jako 'Skryt' a tlačítko se změní na 'Vrátit do žebříčku'
    admin_page2 = client.get("/admin").text
    assert "Skryt" in admin_page2
    assert "Vrátit do žebříčku" in admin_page2

    # 4. Veřejný žebříček studenta již neobsahuje
    client.cookies.set(server.SESSION_COOKIE, cookie_user)
    lb_after = client.get("/api/leaderboard").json()
    assert not any(u["username"] == "CheaterX" for u in lb_after["leaderboard"])
    assert lb_after["rank"] == "-"

    # Přidat záznam do arény (FFA, KotH)
    scoring.submit_ffa_run(uid, "CheaterX", 10, 10, time_ms=1000)
    scoring.submit_koth_challenge(uid, "CheaterX", 10, 10, time_ms=1000)

    # V aréně je skrytý
    ffa_st = scoring.get_ffa_status()
    assert not any(u["username"] == "CheaterX" for u in ffa_st["leaderboard"])
    koth_st = scoring.get_koth_status()
    assert koth_st["king"] is None or koth_st["king"]["username"] != "CheaterX"

    # 5. Admin otestuje fine-tuned reset (pouze body, pouze streaky, pouze arénu, all)
    scoring.record_question_answer(uid, "1-2", True)
    scoring.submit_ffa_run(uid, "CheaterX", 5, 10, time_ms=2000)
    client.cookies.set(server.SESSION_COOKIE, admin_token)
    csrf_token2 = client.cookies.get("csrf_token")

    # Reset pouze bodů
    res_points = client.post("/admin/leaderboard/reset", data={"user_id": uid, "scope": "points", "csrf_token": csrf_token2}, follow_redirects=False)
    assert res_points.status_code == 303
    row = db.get_db().execute("SELECT total_points, current_streak FROM user_scores WHERE user_id = ?", (uid,)).fetchone()
    assert row["total_points"] == 0
    assert row["current_streak"] > 0

    # Reset pouze streaků
    res_streaks = client.post("/admin/leaderboard/reset", data={"user_id": uid, "scope": "streaks", "csrf_token": csrf_token2}, follow_redirects=False)
    assert res_streaks.status_code == 303
    row = db.get_db().execute("SELECT total_points, current_streak, best_streak FROM user_scores WHERE user_id = ?", (uid,)).fetchone()
    assert row["current_streak"] == 0
    assert row["best_streak"] == 0

    # Reset all
    res_reset = client.post("/admin/leaderboard/reset", data={"user_id": uid, "scope": "all", "csrf_token": csrf_token2}, follow_redirects=False)
    assert res_reset.status_code == 303

    # Ověřit vynulování streaků v db
    u_score = db.get_db().execute("SELECT * FROM user_scores WHERE user_id = ?", (uid,)).fetchone()
    assert u_score["total_points"] == 0
    assert u_score["current_streak"] == 0
    assert u_score["best_streak"] == 0
    assert u_score["daily_streak"] == 0
    assert u_score["best_daily_streak"] == 0

    # 6. Admin vrátí studenta do žebříčku (má 0 bodů i po vrácení)
    client.post("/admin/leaderboard/toggle", data={"user_id": uid, "csrf_token": csrf_token2}, follow_redirects=False)
    client.cookies.set(server.SESSION_COOKIE, cookie_user)
    lb_restored = client.get("/api/leaderboard").json()
    ch_user = next((u for u in lb_restored["leaderboard"] if u["username"] == "CheaterX"), None)
    assert ch_user is not None
    assert ch_user["points"] == 0

