"""لایه دیتابیس SQLite — مشترک بین ربات (نویسنده) و پنل (خوانده/نویسنده).

چون دو پروسه‌ی جدا همزمان به فایل دسترسی دارند، WAL روشن شده
تا خواندن و نوشتن موازی بدون قفل شدن انجام شود.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    chat_id     INTEGER PRIMARY KEY,
    first_name  TEXT,
    username    TEXT,
    joined_at   TEXT DEFAULT (datetime('now', 'localtime')),
    last_seen   TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER,
    direction   TEXT,              -- 'in' از کاربر، 'out' از ربات
    text        TEXT,
    created_at  TEXT DEFAULT (datetime('now', 'localtime'))
);
"""


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as db:
        db.executescript(_SCHEMA)


def upsert_user(chat_id: int, first_name: str | None, username: str | None) -> None:
    with get_db() as db:
        db.execute(
            """
            INSERT INTO users (chat_id, first_name, username, last_seen)
            VALUES (?, ?, ?, datetime('now', 'localtime'))
            ON CONFLICT(chat_id) DO UPDATE SET
                first_name = excluded.first_name,
                username   = excluded.username,
                last_seen  = excluded.last_seen
            """,
            (chat_id, first_name, username),
        )


def log_message(chat_id: int, direction: str, text: str) -> None:
    with get_db() as db:
        db.execute(
            "INSERT INTO messages (chat_id, direction, text) VALUES (?, ?, ?)",
            (chat_id, direction, (text or "")[:2000]),
        )


def get_stats() -> dict:
    init_db()
    with get_db() as db:
        users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        msgs_in = db.execute(
            "SELECT COUNT(*) FROM messages WHERE direction='in'"
        ).fetchone()[0]
        msgs_out = db.execute(
            "SELECT COUNT(*) FROM messages WHERE direction='out'"
        ).fetchone()[0]
        today = db.execute(
            "SELECT COUNT(*) FROM messages "
            "WHERE date(created_at) = date('now', 'localtime')"
        ).fetchone()[0]
    return {"users": users, "in": msgs_in, "out": msgs_out, "today": today}


def get_users():
    init_db()
    with get_db() as db:
        return db.execute(
            "SELECT chat_id, first_name, username, joined_at, last_seen "
            "FROM users ORDER BY last_seen DESC"
        ).fetchall()


def get_recent_messages(limit: int = 100):
    init_db()
    with get_db() as db:
        return db.execute(
            "SELECT m.id, m.chat_id, u.first_name, m.direction, m.text, m.created_at "
            "FROM messages m LEFT JOIN users u ON u.chat_id = m.chat_id "
            "ORDER BY m.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
