import sqlite3
from datetime import datetime

DB_PATH = "keys.db"
KEY_ROOMS = ("A411", "A413")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_room    TEXT NOT NULL,
            borrower_room TEXT NOT NULL,
            photo_file_id TEXT,
            given_at      TEXT NOT NULL,
            returned_at   TEXT
        );
        """)
        conn.executemany(
            "INSERT OR IGNORE INTO rooms (code) VALUES (?)",
            [(room,) for room in KEY_ROOMS],
        )


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


def get_rooms():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM rooms ORDER BY code").fetchall()