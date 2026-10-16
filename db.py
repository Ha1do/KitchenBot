import sqlite3
from datetime import datetime, timezone

DB_PATH = "keys.db"
KEY_ROOMS = ("A411", "A413")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            name  TEXT NOT NULL,
            room  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS rooms (
            code        TEXT PRIMARY KEY,
            borrowed_by TEXT,
            since       TEXT
        );

        CREATE TABLE IF NOT EXISTS history (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_room       TEXT NOT NULL,
            borrower_room    TEXT NOT NULL,
            photo_file_id    TEXT,
            photo_chat_id    INTEGER,
            photo_message_id INTEGER,
            given_at         TEXT NOT NULL,
            returned_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS panel (
            id         INTEGER PRIMARY KEY CHECK (id = 1),
            chat_id    INTEGER NOT NULL,
            message_id INTEGER NOT NULL
        );
        """)
        conn.executemany(
            "INSERT OR IGNORE INTO rooms (code) VALUES (?)",
            [(room,) for room in KEY_ROOMS],
        )


# ---------- пользователи ----------

def add_user(tg_id: int, name: str, room: str):
    if room not in KEY_ROOMS:
        raise ValueError(f"Комната {room!r} не из списка {KEY_ROOMS}")
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users (tg_id, name, room) VALUES (?, ?, ?)",
            (tg_id, name, room),
        )


def get_user(tg_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE tg_id = ?", (tg_id,)
        ).fetchone()


# ---------- ключи ----------

def get_rooms():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM rooms ORDER BY code").fetchall()


def give_key(owner_room, borrower_room, file_id, chat_id, message_id, given_at) -> bool:
    """Выдать ключ. False, если он уже выдан. Проверка и запись идут одной операцией."""
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE rooms SET borrowed_by = ?, since = ? "
            "WHERE code = ? AND borrowed_by IS NULL",
            (borrower_room, given_at, owner_room),
        )
        if cur.rowcount == 0:
            return False
        conn.execute(
            "INSERT INTO history (owner_room, borrower_room, photo_file_id, "
            "photo_chat_id, photo_message_id, given_at) VALUES (?, ?, ?, ?, ?, ?)",
            (owner_room, borrower_room, file_id, chat_id, message_id, given_at),
        )
        return True


def return_key(owner_room: str, returned_at: str) -> bool:
    """Вернуть ключ. False, если он и так дома."""
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE rooms SET borrowed_by = NULL, since = NULL "
            "WHERE code = ? AND borrowed_by IS NOT NULL",
            (owner_room,),
        )
        if cur.rowcount == 0:
            return False
        conn.execute(
            "UPDATE history SET returned_at = ? "
            "WHERE owner_room = ? AND returned_at IS NULL",
            (returned_at, owner_room),
        )
        return True


def last_history(limit: int = 5):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


# ---------- панель ----------

def set_panel(chat_id: int, message_id: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO panel (id, chat_id, message_id) VALUES (1, ?, ?)",
            (chat_id, message_id),
        )


def get_panel():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM panel WHERE id = 1").fetchone()