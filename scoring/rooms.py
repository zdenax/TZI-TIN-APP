"""Kompetitivní lobby: místnosti pro FFA, duel a KotH."""
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from db import get_db
from .constants import KOTH_DEFAULT_QUESTIONS, ROOM_LOBBY_TIMEOUT_SECONDS
from .duel import submit_duel_match
from .ffa import submit_ffa_run
from .koth import submit_koth_challenge


# ==============================================================================
# KOMPETITIVNÍ LOBBY & ROOMS (FFA, 1v1 Duel, King of the Hill)
# ==============================================================================

def _waiting_expiry_seconds(created_at: Any, status: str) -> Optional[int]:
    if status != "waiting" or not created_at:
        return None
    try:
        dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - dt).total_seconds()
        return max(0, min(ROOM_LOBBY_TIMEOUT_SECONDS, int(round(ROOM_LOBBY_TIMEOUT_SECONDS - elapsed))))
    except Exception:
        return None


def _cleanup_expired_waiting_rooms(conn, ttl_seconds: int = ROOM_LOBBY_TIMEOUT_SECONDS) -> int:
    """Smaže neodstartované ('waiting') místnosti po vypršení TTL i prázdné opuštěné místnosti."""
    cutoff = f"-{int(ttl_seconds)} seconds"
    with conn:
        cur = conn.execute(
            """
            DELETE FROM comp_rooms
            WHERE (status = 'waiting' AND datetime(created_at) <= datetime('now', ?))
               OR (
                   status IN ('waiting', 'in_progress')
                   AND NOT EXISTS (SELECT 1 FROM comp_room_players p WHERE p.room_id = comp_rooms.id)
               )
            """,
            (cutoff,),
        )
    return cur.rowcount or 0


def _format_room(conn, room_row) -> Dict[str, Any]:
    import json
    if not room_row:
        return {}
    r = dict(room_row)
    rid = r["id"]
    players_rows = conn.execute(
        """
        SELECT user_id, username, is_host, status, score, correct_count, total_questions, time_ms, joined_at, finished_at
        FROM comp_room_players
        WHERE room_id = ?
        ORDER BY CASE WHEN status = 'finished' THEN 0 ELSE 1 END, score DESC, time_ms ASC, is_host DESC, joined_at ASC
        """,
        (rid,)
    ).fetchall()
    players = [dict(p) for p in players_rows]
    try:
        q_ids = json.loads(r.get("question_ids_json") or "[]")
    except Exception:
        q_ids = []
    return {
        "id": rid,
        "name": r["name"],
        "mode": r["mode"],
        "host_id": r["host_id"],
        "host_username": r["host_username"],
        "status": r["status"],
        "max_players": r["max_players"],
        "question_count": r["question_count"],
        "source": r.get("source") or "",
        "question_ids": q_ids,
        "player_count": len(players),
        "players": players,
        "winner_id": r.get("winner_id"),
        "winner_username": r.get("winner_username"),
        "created_at": r.get("created_at"),
        "started_at": r.get("started_at"),
        "completed_at": r.get("completed_at"),
        "expires_in_seconds": _waiting_expiry_seconds(r.get("created_at"), r["status"]),
        "lobby_timeout_seconds": ROOM_LOBBY_TIMEOUT_SECONDS,
    }


def list_comp_rooms(user_id: Optional[int] = None) -> Dict[str, Any]:
    """Vrátí seznam čekajících, probíhajících a nedávno dokončených místností v lobby."""
    conn = get_db()
    _cleanup_expired_waiting_rooms(conn)
    active_rows = conn.execute(
        """
        SELECT * FROM comp_rooms
        WHERE status IN ('waiting', 'in_progress')
        ORDER BY CASE WHEN status = 'waiting' THEN 0 ELSE 1 END, id DESC
        LIMIT 20
        """
    ).fetchall()
    recent_rows = conn.execute(
        """
        SELECT * FROM comp_rooms
        WHERE status = 'completed'
        ORDER BY id DESC
        LIMIT 10
        """
    ).fetchall()
    return {
        "active_rooms": [_format_room(conn, row) for row in active_rows],
        "recent_rooms": [_format_room(conn, row) for row in recent_rows],
    }


SQLITE_MAX_INT = 9223372036854775807


def _valid_id(val: Any) -> bool:
    return isinstance(val, int) and not isinstance(val, bool) and 1 <= val <= SQLITE_MAX_INT


def get_comp_room(room_id: int) -> Optional[Dict[str, Any]]:
    if not _valid_id(room_id):
        return None
    conn = get_db()
    _cleanup_expired_waiting_rooms(conn)
    row = conn.execute("SELECT * FROM comp_rooms WHERE id = ?", (int(room_id),)).fetchone()
    if not row:
        return None
    return _format_room(conn, row)


def create_comp_room(
    user_id: int,
    username: str,
    mode: str = "ffa",
    name: str = "",
    question_count: int = KOTH_DEFAULT_QUESTIONS,
    source: str = "",
    question_ids: Optional[List[str]] = None,
    max_players: Optional[int] = None,
) -> Dict[str, Any]:
    """Vytvoří novou kompetitivní místnost v lobby a nastaví zakladatele jako 👑 hostitele."""
    import json
    conn = get_db()
    _cleanup_expired_waiting_rooms(conn)
    mode_clean = mode if mode in ("ffa", "duel", "koth") else "ffa"
    mode_labels = {"ffa": "Free For All", "duel": "1v1 Duel", "koth": "King of the Hill"}
    room_name = (name or "").strip()[:60] or f"{mode_labels[mode_clean]} – {username}"
    max_p = int(max_players) if max_players else (2 if mode_clean == "duel" else 8)
    max_p = max(2, min(16, max_p))
    q_count = max(1, min(30, int(question_count or KOTH_DEFAULT_QUESTIONS)))

    with conn:
        cur = conn.execute(
            """
            INSERT INTO comp_rooms (name, mode, host_id, host_username, status, max_players, question_count, source, question_ids_json)
            VALUES (?, ?, ?, ?, 'waiting', ?, ?, ?, ?)
            """,
            (room_name, mode_clean, user_id, username, max_p, q_count, source or "", json.dumps(question_ids or []))
        )
        room_id = cur.lastrowid
        conn.execute(
            """
            INSERT INTO comp_room_players (room_id, user_id, username, is_host, status, total_questions)
            VALUES (?, ?, ?, 1, 'joined', ?)
            """,
            (room_id, user_id, username, q_count)
        )

    return get_comp_room(room_id)


def join_comp_room(room_id: int, user_id: int, username: str, auto_start_duel: bool = False) -> Dict[str, Any]:
    """Připojí hráče do čekající místnosti v lobby."""
    if not _valid_id(room_id):
        return {"ok": False, "error": "Místnost neexistuje."}
    conn = get_db()
    _cleanup_expired_waiting_rooms(conn)
    with conn:
        row = conn.execute("SELECT * FROM comp_rooms WHERE id = ?", (int(room_id),)).fetchone()
        if not row:
            return {"ok": False, "error": "Místnost již vypršela (limit 5 minut bez spuštění) nebo neexistuje."}

        existing = conn.execute(
            "SELECT * FROM comp_room_players WHERE room_id = ? AND user_id = ?",
            (int(room_id), user_id)
        ).fetchone()

        if row["status"] != "waiting" and not existing:
            return {"ok": False, "error": "Tato místnost již byla spuštěna nebo ukončena."}

        if not existing:
            cnt_row = conn.execute(
                "SELECT COUNT(*) AS c FROM comp_room_players WHERE room_id = ?",
                (int(room_id),)
            ).fetchone()
            cur_count = cnt_row["c"] if cnt_row else 0
            if cur_count >= row["max_players"]:
                return {"ok": False, "error": "Místnost je již plná."}

            conn.execute(
                """
                INSERT INTO comp_room_players (room_id, user_id, username, is_host, status, total_questions)
                VALUES (?, ?, ?, 0, 'joined', ?)
                """,
                (int(room_id), user_id, username, row["question_count"])
            )

        if auto_start_duel and row["mode"] == "duel":
            cnt_after = conn.execute(
                "SELECT COUNT(*) AS c FROM comp_room_players WHERE room_id = ?",
                (int(room_id),)
            ).fetchone()["c"]
            if cnt_after >= 2 and row["status"] == "waiting":
                conn.execute(
                    "UPDATE comp_rooms SET status = 'in_progress', started_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (int(room_id),)
                )
                conn.execute(
                    "UPDATE comp_room_players SET status = 'playing' WHERE room_id = ?",
                    (int(room_id),)
                )

    return {"ok": True, "room": get_comp_room(room_id)}


def start_comp_room(room_id: int, user_id: int) -> Dict[str, Any]:
    """Hostitel (👑) spustí hru pro všechny připojené hráče v místnosti."""
    if not _valid_id(room_id):
        return {"ok": False, "error": "Místnost neexistuje."}
    conn = get_db()
    _cleanup_expired_waiting_rooms(conn)
    with conn:
        row = conn.execute("SELECT * FROM comp_rooms WHERE id = ?", (int(room_id),)).fetchone()
        if not row:
            return {"ok": False, "error": "Místnost již vypršela (limit 5 minut bez spuštění) nebo neexistuje."}
        if row["host_id"] != user_id:
            return {"ok": False, "error": "Pouze zakladatel místnosti (👑) může hru spustit."}
        if row["status"] == "waiting":
            conn.execute(
                "UPDATE comp_rooms SET status = 'in_progress', started_at = CURRENT_TIMESTAMP WHERE id = ?",
                (int(room_id),)
            )
            conn.execute(
                "UPDATE comp_room_players SET status = 'playing' WHERE room_id = ?",
                (int(room_id),)
            )
    return {"ok": True, "room": get_comp_room(room_id)}


def leave_comp_room(room_id: int, user_id: int) -> Dict[str, Any]:
    """Hráč opustí místnost. Pokud odejde 👑 hostitel z čekající místnosti, předá se korunka dalšímu hráči nebo se prázdná místnost zruší."""
    if not _valid_id(room_id):
        return {"ok": True, "deleted": True}
    conn = get_db()
    _cleanup_expired_waiting_rooms(conn)
    with conn:
        row = conn.execute("SELECT * FROM comp_rooms WHERE id = ?", (int(room_id),)).fetchone()
        if not row:
            return {"ok": True, "deleted": True}
        conn.execute(
            "DELETE FROM comp_room_players WHERE room_id = ? AND user_id = ?",
            (int(room_id), user_id)
        )
        rem = conn.execute(
            "SELECT * FROM comp_room_players WHERE room_id = ? ORDER BY joined_at ASC",
            (int(room_id),)
        ).fetchall()
        if not rem:
            conn.execute("DELETE FROM comp_rooms WHERE id = ?", (int(room_id),))
            return {"ok": True, "deleted": True}
        if row["host_id"] == user_id:
            new_host = rem[0]
            conn.execute(
                "UPDATE comp_rooms SET host_id = ?, host_username = ? WHERE id = ?",
                (new_host["user_id"], new_host["username"], int(room_id))
            )
            conn.execute(
                "UPDATE comp_room_players SET is_host = 1 WHERE room_id = ? AND user_id = ?",
                (int(room_id), new_host["user_id"])
            )
    return {"ok": True, "deleted": False, "room": get_comp_room(room_id)}


def submit_comp_room_result(
    room_id: int,
    user_id: int,
    username: str,
    correct_count: int,
    total_questions: int,
    time_ms: int = 0,
) -> Dict[str, Any]:
    """Zaznamená výsledek hráče v místnosti, aktualizuje pořadí v místnosti i globální statistiky daného režimu."""
    conn = get_db()
    row = conn.execute("SELECT * FROM comp_rooms WHERE id = ?", (int(room_id),)).fetchone()
    if not row:
        return {"ok": False, "error": "Místnost neexistuje."}

    if row["status"] != "in_progress":
        return {"ok": False, "error": "Místnost není ve stavu in_progress."}

    time_ms_clean = max(0, int(time_ms or 0))
    correct_clean = max(0, int(correct_count or 0))
    total_clean = max(1, int(total_questions or row["question_count"] or KOTH_DEFAULT_QUESTIONS))

    speed_bonus = max(0, 120 - (time_ms_clean // 1000)) if correct_clean > 0 else 0
    score = correct_clean * 100 + speed_bonus

    mode = row["mode"]
    with conn:
        existing = conn.execute(
            "SELECT * FROM comp_room_players WHERE room_id = ? AND user_id = ?",
            (int(room_id), user_id)
        ).fetchone()
        if not existing:
            return {"ok": False, "error": "Hráč není připojen v této místnosti."}

        conn.execute(
            """
            UPDATE comp_room_players
            SET status = 'finished', score = ?, correct_count = ?, total_questions = ?, time_ms = ?, finished_at = CURRENT_TIMESTAMP
            WHERE room_id = ? AND user_id = ?
            """,
            (score, correct_clean, total_clean, time_ms_clean, int(room_id), user_id)
        )

        p_rows = conn.execute(
            """
            SELECT * FROM comp_room_players
            WHERE room_id = ?
            ORDER BY CASE WHEN status = 'finished' THEN 0 ELSE 1 END, score DESC, time_ms ASC
            """,
            (int(room_id),)
        ).fetchall()

        all_finished = len(p_rows) > 0 and all(p["status"] == "finished" for p in p_rows)
        finished_rows = [p for p in p_rows if p["status"] == "finished"]
        leader = finished_rows[0] if finished_rows else None

        if all_finished and leader:
            conn.execute(
                """
                UPDATE comp_rooms
                SET status = 'completed', winner_id = ?, winner_username = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (leader["user_id"], leader["username"], int(room_id))
            )

    # Propíšeme i do globální tabulky příslušného kompetitivního režimu
    mode_res = {}
    if mode == "koth":
        mode_res = submit_koth_challenge(user_id, username, correct_clean, total_clean, time_ms_clean)
    elif mode == "ffa":
        mode_res = submit_ffa_run(user_id, username, correct_clean, total_clean, time_ms_clean)
    elif mode == "duel":
        mode_res = submit_duel_match(user_id, username, correct_clean, total_clean, time_ms_clean)

    room_after = get_comp_room(room_id)
    rank_in_room = 1
    for idx, p in enumerate(room_after.get("players", []), 1):
        if p["user_id"] == user_id:
            rank_in_room = idx
            break

    return {
        "ok": True,
        "room_id": int(room_id),
        "mode": mode,
        "score": score,
        "challenger_score": score,
        "my_score": score,
        "correct_count": correct_clean,
        "total_questions": total_clean,
        "time_ms": time_ms_clean,
        "rank": rank_in_room,
        "is_leader": rank_in_room == 1,
        "won_throne": mode_res.get("won_throne", rank_in_room == 1),
        "previous_king_score": mode_res.get("previous_king_score", 0),
        "resolved": room_after.get("status") == "completed",
        "won_duel": rank_in_room == 1 and room_after.get("status") == "completed",
        "room": room_after,
        "mode_result": mode_res,
    }
