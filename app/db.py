import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import get_db_path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    login TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'admin'))
);

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    building TEXT NOT NULL CHECK (building IN ('A', 'B', 'C', 'D')),
    floor INTEGER NOT NULL CHECK (floor >= 1),
    capacity INTEGER NOT NULL CHECK (capacity > 0),
    equipment TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY,
    room_id INTEGER NOT NULL REFERENCES rooms(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'cancelled')),
    comment TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_bookings_room_date_status
    ON bookings (room_id, date, status);
"""


def get_connection() -> sqlite3.Connection:
    """Открывает соединение с SQLite в режиме ручного управления транзакциями."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(db_path),
        check_same_thread=False,
        isolation_level=None,
        timeout=10.0,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection | None = None) -> None:
    """Создаёт таблицы и индексы, если их ещё нет."""
    owns_conn = conn is None
    target = conn or get_connection()
    try:
        target.executescript(SCHEMA_SQL)
    finally:
        if owns_conn:
            target.close()


@contextmanager
def transaction(
    conn: sqlite3.Connection, *, immediate: bool = False
) -> Iterator[sqlite3.Connection]:
    """Обёртка над транзакцией; при immediate=True сразу берёт блокировку на запись."""
    conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
