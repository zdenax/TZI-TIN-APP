"""Automatická synchronizace bank otázek z upstream repozitáře (zdenax/TZI-TIN-APP)."""
import time
import subprocess
from .config import BASE
from .questions import refresh_questions


UPSTREAM_URL = "https://github.com/zdenax/TZI-TIN-APP.git"


def _ensure_upstream_remote():
    """Zajistí existenci git remote 'upstream' mířícího na zdenax/TZI-TIN-APP."""
    res = subprocess.run(["git", "remote", "get-url", "upstream"], cwd=BASE, capture_output=True, text=True)
    if res.returncode != 0:
        subprocess.run(["git", "remote", "add", "upstream", UPSTREAM_URL], cwd=BASE, capture_output=True, text=True)
    elif UPSTREAM_URL not in res.stdout:
        subprocess.run(["git", "remote", "set-url", "upstream", UPSTREAM_URL], cwd=BASE, capture_output=True, text=True)


# --- Git Auto-sync Worker (pouze banky otázek z upstream/main) ---
def git_pull():
    try:
        _ensure_upstream_remote()
        print("[Auto-sync] Kontroluji nové banky otázek z upstream/main (zdenax/TZI-TIN-APP)...")
        fetch_res = subprocess.run(
            ["git", "fetch", "upstream", "main"],
            cwd=BASE, capture_output=True, text=True, timeout=30
        )
        if fetch_res.returncode != 0:
            err = (fetch_res.stdout + "\n" + fetch_res.stderr).strip()
            print(f"[Auto-sync] Chyba při git fetch upstream: {err}")
            return err

        checkout_res = subprocess.run(
            ["git", "checkout", "upstream/main", "--", ":(glob)banky/*.json", "glosar"],
            cwd=BASE, capture_output=True, text=True, timeout=30
        )
        out = (checkout_res.stdout + "\n" + checkout_res.stderr).strip()

        # Okamžitě obnovit cache otázek v paměti běžícího serveru
        refresh_questions()

        # Pokud se v banky/ nebo glosar/ něco změnilo, commitnout a pushnout do vlastního forku (origin)
        status_res = subprocess.run(
            ["git", "status", "--porcelain", "--", ":(glob)banky/*.json", "glosar"],
            cwd=BASE, capture_output=True, text=True, timeout=15
        )
        if status_res.stdout.strip():
            subprocess.run(["git", "add", "--", ":(glob)banky/*.json", "glosar"], cwd=BASE, capture_output=True, text=True, timeout=15)
            subprocess.run(
                ["git", "commit", "--only", "-m", "chore(banky): auto-sync question banks from upstream/main", "--", ":(glob)banky/*.json", "glosar"],
                cwd=BASE, capture_output=True, text=True, timeout=15
            )
            push_res = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=BASE, capture_output=True, text=True, timeout=30
            )
            out = (out + f"\n[Auto-sync] Nové banky uloženy a pushnuty do origin/main ({push_res.returncode}).").strip()
        else:
            out = "Banky otázek jsou aktuální vůči upstream/main."

        print(f"[Auto-sync] Výsledek: {out}")
        return out
    except Exception as e:
        print(f"[Auto-sync] Chyba: {e}")
        return str(e)


def sync_worker():
    while True:
        time.sleep(15 * 60)
        git_pull()
