"""
database.py — Dual-backend DB layer (Supabase preferred, SQLite fallback).
All public functions are async-compatible via run_in_executor for SQLite.
"""
import os, sqlite3, json
from datetime import datetime, date
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SQLITE_PATH   = os.getenv("SQLITE_DB_PATH", "attendance.db")

# ── Choose backend ─────────────────────────────────────────────────────────────
USE_SUPABASE = bool(SUPABASE_URL and "your-project" not in SUPABASE_URL)

if USE_SUPABASE:
    from supabase import create_client, Client
    _sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ══════════════════════════════════════════════════════════════════════════════
# SQLite bootstrap
# ══════════════════════════════════════════════════════════════════════════════
def _sqlite_init():
    con = sqlite3.connect(SQLITE_PATH)
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            custom_id   TEXT UNIQUE NOT NULL,
            full_name   TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'student',
            photo_url   TEXT,
            parent_phone TEXT,
            parent_email TEXT,
            secret_key  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attendance_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            scan_type   TEXT NOT NULL,
            scanned_at  TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    """)
    con.commit()
    con.close()


def _sqlite_conn():
    con = sqlite3.connect(SQLITE_PATH)
    con.row_factory = sqlite3.Row
    return con


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════
def get_user_by_custom_id(custom_id: str) -> Optional[dict]:
    if USE_SUPABASE:
        res = _sb.table("users").select("*").eq("custom_id", custom_id).single().execute()
        return res.data
    con = _sqlite_conn()
    row = con.execute("SELECT * FROM users WHERE custom_id=?", (custom_id,)).fetchone()
    con.close()
    return dict(row) if row else None


def get_last_log_today(user_id: int) -> Optional[dict]:
    today = date.today().isoformat()
    if USE_SUPABASE:
        res = (
            _sb.table("attendance_logs")
            .select("*")
            .eq("user_id", user_id)
            .gte("scanned_at", f"{today}T00:00:00")
            .order("scanned_at", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    con = _sqlite_conn()
    row = con.execute(
        "SELECT * FROM attendance_logs WHERE user_id=? AND scanned_at>=? ORDER BY scanned_at DESC LIMIT 1",
        (user_id, f"{today}T00:00:00"),
    ).fetchone()
    con.close()
    return dict(row) if row else None


def get_recent_log(user_id: int, within_seconds: int = 120) -> Optional[dict]:
    """Return the most recent log within `within_seconds` to prevent duplicate scans."""
    from datetime import timezone, timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=within_seconds)).isoformat()
    if USE_SUPABASE:
        res = (
            _sb.table("attendance_logs")
            .select("*")
            .eq("user_id", user_id)
            .gte("scanned_at", cutoff)
            .order("scanned_at", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    con = _sqlite_conn()
    row = con.execute(
        "SELECT * FROM attendance_logs WHERE user_id=? AND scanned_at>=? ORDER BY scanned_at DESC LIMIT 1",
        (user_id, cutoff),
    ).fetchone()
    con.close()
    return dict(row) if row else None


def insert_log(user_id: int, scan_type: str) -> dict:
    now = datetime.utcnow().isoformat()
    if USE_SUPABASE:
        res = _sb.table("attendance_logs").insert(
            {"user_id": user_id, "scan_type": scan_type, "scanned_at": now}
        ).execute()
        return res.data[0]
    con = _sqlite_conn()
    cur = con.execute(
        "INSERT INTO attendance_logs(user_id, scan_type, scanned_at) VALUES(?,?,?)",
        (user_id, scan_type, now),
    )
    con.commit()
    row_id = cur.lastrowid
    con.close()
    return {"id": row_id, "user_id": user_id, "scan_type": scan_type, "scanned_at": now}


def get_logs_today(limit: int = 50) -> list:
    today = date.today().isoformat()
    if USE_SUPABASE:
        res = (
            _sb.table("attendance_logs")
            .select("*, users(custom_id, full_name, role, photo_url)")
            .gte("scanned_at", f"{today}T00:00:00")
            .order("scanned_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    con = _sqlite_conn()
    rows = con.execute(
        """SELECT l.*, u.custom_id, u.full_name, u.role, u.photo_url
           FROM attendance_logs l JOIN users u ON l.user_id=u.id
           WHERE l.scanned_at>=? ORDER BY l.scanned_at DESC LIMIT ?""",
        (f"{today}T00:00:00", limit),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def seed_demo_users():
    """Insert demo users if the table is empty (SQLite only)."""
    if USE_SUPABASE:
        return
    import hmac, hashlib, base64
    master = os.getenv("MASTER_SECRET", "change_me")
    def make_secret(cid):
        return base64.b32encode(
            hmac.new(master.encode(), cid.encode(), hashlib.sha256).digest()
        ).decode()

    demos = [
        ("STU001", "Alice Reyes",   "student", None, "+639171234567", "alice@example.com"),
        ("STU002", "Bob Santos",    "student", None, "+639179876543", "bob@example.com"),
        ("TCH001", "Ms. Cruz",      "teacher", None, "+639175551234", "cruz@example.com"),
    ]
    con = _sqlite_conn()
    for cid, name, role, photo, phone, email in demos:
        con.execute(
            "INSERT OR IGNORE INTO users(custom_id,full_name,role,photo_url,parent_phone,parent_email,secret_key)"
            " VALUES(?,?,?,?,?,?,?)",
            (cid, name, role, photo, phone, email, make_secret(cid)),
        )
    con.commit()
    con.close()


# Initialise on import
if not USE_SUPABASE:
    _sqlite_init()
    seed_demo_users()
