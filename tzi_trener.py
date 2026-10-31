#!/usr/bin/env python3
"""TZI Trenér: kvíz na opakování přednášek z Teoretické informatiky (KI/TIN).

Deklarace využití AI: vytvořeno s pomocí nástroje Claude Sonnet 5.5 (Anthropic, 2026),
uvedeno v souladu se Směrnicí rektora UJEP č. 7/2026 (dobrovolně).

Spuštění:  python3 tzi_trener.py            # http://127.0.0.1:5051, otevře se prohlížeč
           python3 tzi_trener.py --lan      # navíc dostupné v místní síti (telefon)
           python3 tzi_trener.py --klasicky # výchozí je starý vzhled (jinak nový; přepínač je i v menu)
Bez závislostí (jen standardní knihovna). Banky otázek jsou v banky/*.json, jedna na přednášku.
"""
import json
import os
import socket
import sys
import threading
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE = Path(__file__).resolve().parent
BANKS = BASE / "banky"
RECALL_DIR = BANKS / "doplnovacka"  # otázky typu recall; běžné režimy čtou jen banky/*.json, tyhle nevidí
PROGRESS_FILE = BASE / "progress.json"
PORT = 5051
ALL = "_all"
lock = threading.Lock()


def load_banks():
    """Vrátí {id: {title, date, lecture, questions}} seřazené podle čísla přednášky."""
    banks = {}
    for p in sorted(BANKS.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        banks[p.stem] = d
    return dict(sorted(banks.items(), key=lambda kv: kv[1].get("lecture", 0)))


def source_label(d):
    y, m, day = d["date"].split("-")
    return f'{d["lecture"]}. přednáška ({int(day)}. {int(m)}. {y}): {d["title"]}'


def list_sources():
    banks = load_banks()
    out = [{"id": k, "label": source_label(d), "count": len(d["questions"])} for k, d in banks.items()]
    if len(out) > 1:
        out.append({"id": ALL, "label": "Všechny přednášky dohromady",
                    "count": sum(s["count"] for s in out)})
    return out


def load_questions(source):
    banks = load_banks()
    if source == ALL:
        return [q for d in banks.values() for q in d["questions"]]
    return banks[source]["questions"]


def load_recall():
    """Otázky pro režim Doplňovačka ze všech bank v banky/doplnovacka/."""
    return [q for p in sorted(RECALL_DIR.glob("*.json"))
            for q in json.loads(p.read_text(encoding="utf-8"))["questions"]]


def load_progress():
    try:
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"seen": {}, "sessions": {}}


def save_progress(data):
    PROGRESS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


UI_DIR = BASE / "ui"
UI_FILES = {"novy": "novy.html", "klasicky": "klasicky.html"}
AUTOMAT_FILES = {"/automat": ("text/html; charset=utf-8", "automat.html"),
                "/automat-core.js": ("text/javascript; charset=utf-8", "automat-core.js")}
DEFAULT_UI = "novy"
UI_COOKIE = "tzi_ui"


def pick_ui(query, cookie_header):
    """Vrátí (název UI, zda ho nastavit do cookie). Pořadí: ?ui= v adrese, cookie, výchozí."""
    wanted = query.get("ui", [""])[0]
    if wanted in UI_FILES:
        return wanted, True
    c = SimpleCookie(cookie_header or "").get(UI_COOKIE)
    if c and c.value in UI_FILES:
        return c.value, False
    return DEFAULT_UI, False


def load_ui(name):
    return (UI_DIR / UI_FILES[name]).read_text(encoding="utf-8")


MAX_BODY = 1_000_000


def host_ok(host_header):
    """Povolí localhost a IP adresy, odmítne cizí jména (ochrana proti DNS rebinding)."""
    host = (host_header or "").rsplit(":", 1)[0] if not (host_header or "").startswith("[") else ""
    if host in ("localhost", "127.0.0.1"):
        return True
    try:
        socket.inet_aton(host)
        return True
    except OSError:
        return False


class Handler(BaseHTTPRequestHandler):
    def _guard(self, post=False):
        """Vrátí True, když je požadavek v pořádku; jinak pošle chybu."""
        if not host_ok(self.headers.get("Host")):
            self._send(403, "forbidden host", "text/plain")
            return False
        if post and self.headers.get("X-TZI") != "1":
            self._send(403, "forbidden", "text/plain")
            return False
        return True

    def _send(self, code, body, ctype="application/json; charset=utf-8", headers=None):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def do_GET(self):
        if not self._guard():
            return
        u = urlparse(self.path)
        q = parse_qs(u.query)
        source = q.get("source", [""])[0]
        if u.path == "/":
            name, remember = pick_ui(q, self.headers.get("Cookie"))
            try:
                page = load_ui(name)
            except OSError:
                return self._send(500, f"Chybí soubor ui/{UI_FILES[name]}", "text/plain; charset=utf-8")
            hdr = {"Set-Cookie": f"{UI_COOKIE}={name}; Path=/; Max-Age=31536000; SameSite=Lax"} if remember else None
            return self._send(200, page, "text/html; charset=utf-8", hdr)
        if u.path in AUTOMAT_FILES:
            ctype, name = AUTOMAT_FILES[u.path]
            try:
                return self._send(200, (UI_DIR / name).read_text(encoding="utf-8"), ctype)
            except OSError:
                return self._send(500, f"Chybí soubor ui/{name}", "text/plain; charset=utf-8")
        if u.path == "/api/sources":
            srcs = list_sources()
            real = [s for s in srcs if s["id"] != ALL]
            default = real[-1]["id"] if real else ""
            return self._json({"sources": srcs, "default": default})
        if u.path == "/api/questions":
            try:
                return self._json(load_questions(source))
            except (KeyError, OSError, ValueError) as e:
                return self._json({"error": str(e)}, 404)
        if u.path == "/api/recall":
            try:
                return self._json(load_recall())
            except (KeyError, OSError, ValueError) as e:
                return self._json({"error": str(e)}, 500)
        if u.path == "/api/progress":
            with lock:
                d = load_progress()
            return self._json({"seen": d.get("seen", {}), "session": d.get("sessions", {}).get(source)})
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        if not self._guard(post=True):
            return
        u = urlparse(self.path)
        if u.path == "/api/progress":
            source = parse_qs(u.query).get("source", [""])[0]
            n = min(int(self.headers.get("Content-Length") or 0), MAX_BODY)
            try:
                payload = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._json({"error": "bad json"}, 400)
            with lock:
                d = load_progress()
                d["seen"] = payload.get("seen", {})
                d.setdefault("sessions", {})[source] = payload.get("session")
                save_progress(d)
            return self._json({"ok": True})
        if u.path == "/shutdown":
            self._send(200, "bye", "text/plain")
            threading.Timer(0.2, lambda: os._exit(0)).start()
            return
        self._send(404, "not found", "text/plain")

    def log_message(self, *args):
        pass


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    if not list(BANKS.glob("*.json")):
        raise SystemExit(f"V {BANKS} nejsou žádné banky otázek. Spusť: python3 build_bank.py")
    global DEFAULT_UI
    if "--klasicky" in sys.argv:
        DEFAULT_UI = "klasicky"
    lan = "--lan" in sys.argv
    host = "0.0.0.0" if lan else "127.0.0.1"
    for port in range(PORT, PORT + 20):
        try:
            httpd = ThreadingHTTPServer((host, port), Handler)
            break
        except OSError:
            continue
    else:
        raise SystemExit(f"Nenašel jsem volný port ({PORT}-{PORT + 19}).")
    url = f"http://127.0.0.1:{port}"
    print(f"TZI Trenér → {url}")
    if lan:
        print(f"V síti (telefon):   http://{lan_ip()}:{port}")
    print("Ukončíš ho tlačítkem v menu nebo přes Ctrl+C.")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nKonec.")


if __name__ == "__main__":
    main()
