"""
Хранилище данных на SQLite. Синхронный sqlite3 достаточно для MVP-нагрузки
(один инстанс бота, небольшой поток пользователей).

Таблицы:
- users     : анкета пользователя (chat_id, username, ответы, результат, статус)
- slots     : свободные / занятые окна для записи (ведёт админ бота)
- bookings  : какой пользователь занял какой слот и когда
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from config import DB_PATH

# --- статусы пользователя, см. раздел "8. Что нужно от заказчика" и п.6 ТЗ ---
STATUS_STARTED = "started"                # нажал /start, квиз не завершён
STATUS_QUIZ_DONE = "quiz_done"            # прошёл тест, увидел результат
STATUS_REACHED_BOOKING = "reached_booking"  # дошёл до экрана записи, но не забронировал
STATUS_BOOKED = "booked"                  # выбрал слот


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                chat_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                answers_json TEXT,           -- список из 8 индексов (1-5) по порядку вопросов
                result_type TEXT,            -- 'single' | 'mixed'
                result_patterns_json TEXT,   -- список индексов паттернов результата (1 или 2 эл-та)
                status TEXT DEFAULT 'started',
                created_at TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_dt TEXT NOT NULL,       -- ISO datetime 'YYYY-MM-DD HH:MM'
                is_booked INTEGER DEFAULT 0,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_id INTEGER NOT NULL REFERENCES slots(id),
                chat_id INTEGER NOT NULL,
                booked_at TEXT
            )
            """
        )


def _now():
    return datetime.utcnow().isoformat(timespec="seconds")


# ---------------------------------------------------------------- users ----

def upsert_user(chat_id: int, username: str | None, full_name: str | None):
    with get_conn() as conn:
        row = conn.execute("SELECT chat_id FROM users WHERE chat_id=?", (chat_id,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (chat_id, username, full_name, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (chat_id, username, full_name, STATUS_STARTED, _now(), _now()),
            )
        else:
            conn.execute(
                "UPDATE users SET username=?, full_name=?, updated_at=? WHERE chat_id=?",
                (username, full_name, _now(), chat_id),
            )


def save_quiz_result(chat_id: int, answers: list[int], result_type: str, patterns: list[int]):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET answers_json=?, result_type=?, result_patterns_json=?, "
            "status=?, updated_at=? WHERE chat_id=?",
            (
                json.dumps(answers),
                result_type,
                json.dumps(patterns),
                STATUS_QUIZ_DONE,
                _now(),
                chat_id,
            ),
        )


def set_status(chat_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET status=?, updated_at=? WHERE chat_id=?",
            (status, _now(), chat_id),
        )


def get_user(chat_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE chat_id=?", (chat_id,)).fetchone()


def list_pending_bookings(older_than_hours: float = 0.0) -> list[sqlite3.Row]:
    """Пользователи со статусом 'дошёл до записи', которые ещё не забронировали слот.
    Используется вручную (/pending) для follow-up в течение суток."""
    cutoff = (datetime.utcnow() - timedelta(hours=older_than_hours)).isoformat(timespec="seconds")
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE status=? AND updated_at<=? ORDER BY updated_at ASC",
            (STATUS_REACHED_BOOKING, cutoff),
        ).fetchall()


# ---------------------------------------------------------------- slots ----

def add_slot(slot_dt: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO slots (slot_dt, is_booked, created_at) VALUES (?, 0, ?)",
            (slot_dt, _now()),
        )
        return cur.lastrowid


def delete_slot(slot_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM slots WHERE id=? AND is_booked=0", (slot_id,))
        return cur.rowcount > 0


def list_available_slots() -> list[sqlite3.Row]:
    now = _now()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM slots WHERE is_booked=0 AND slot_dt>=? ORDER BY slot_dt ASC",
            (now.replace("T", " ")[:16],),
        ).fetchall()


def list_all_slots() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM slots ORDER BY slot_dt ASC").fetchall()


def get_slot(slot_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM slots WHERE id=?", (slot_id,)).fetchone()


def book_slot(slot_id: int, chat_id: int) -> bool:
    """Атомарно бронирует слот, если он ещё свободен. Возвращает True при успехе."""
    with get_conn() as conn:
        cur = conn.execute("UPDATE slots SET is_booked=1 WHERE id=? AND is_booked=0", (slot_id,))
        if cur.rowcount == 0:
            return False
        conn.execute(
            "INSERT INTO bookings (slot_id, chat_id, booked_at) VALUES (?, ?, ?)",
            (slot_id, chat_id, _now()),
        )
        return True
