import argparse
import json
import sqlite3
from datetime import timedelta

from app import clock
from app.db import get_connection, init_db, transaction

SEED_USERS: list[tuple[int, str, str, str]] = [
    (1, "student1", "Иван Студентов", "student"),
    (2, "student2", "Мария Студентова", "student"),
    (3, "admin", "Администратор Пупкин", "admin"),
]

SEED_ROOMS: list[tuple[int, str, str, int, int, list[str]]] = [
    (1, "A-101", "A", 1, 30, ["projector", "whiteboard"]),
    (2, "A-102", "A", 1, 20, ["whiteboard"]),
    (3, "A-203", "A", 2, 15, ["computers", "projector"]),
    (4, "B-101", "B", 1, 40, ["projector", "audio"]),
    (5, "B-204", "B", 2, 25, ["projector", "whiteboard", "audio"]),
    (6, "B-305", "B", 3, 10, ["whiteboard"]),
    (7, "C-110", "C", 1, 50, ["projector", "audio", "video"]),
    (8, "C-210", "C", 2, 35, ["computers"]),
    (9, "C-301", "C", 3, 12, ["whiteboard", "projector"]),
    (10, "D-101", "D", 1, 60, ["projector", "audio", "video"]),
    (11, "D-202", "D", 2, 18, ["whiteboard"]),
    (12, "D-303", "D", 3, 24, ["projector", "computers"]),
]

# (id, room_id, user_id, сдвиг_дней_от_сегодня, start_time, end_time, status, comment)
SEED_BOOKINGS: list[tuple[int, int, int, int, str, str, str, str]] = [
    (1, 1, 1, 1, "10:00", "11:30", "active", "Консультация"),
    (2, 1, 2, 1, "14:00", "15:30", "active", "Подготовка к семинару"),
    (3, 4, 2, 1, "09:00", "10:30", "active", "Собрание группы"),
    (4, 7, 3, 1, "12:00", "14:00", "active", "Встреча с деканом"),
    (5, 1, 1, 0, "15:00", "16:00", "cancelled", "Отменили"),
    (6, 10, 2, 2, "13:00", "15:00", "active", "Лекция"),
    (7, 5, 1, 1, "16:00", "17:30", "active", "Кружок"),
]


def seed_data(conn: sqlite3.Connection, *, force: bool = False) -> bool:
    """Заливает seed-данные в БД. Возвращает False, если база уже не пуста (при force=False)."""
    if not force:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
        if row is not None and row["cnt"] > 0:
            return False

    base_date = clock.today()
    with transaction(conn, immediate=True):
        if force:
            conn.execute("DELETE FROM bookings")
            conn.execute("DELETE FROM rooms")
            conn.execute("DELETE FROM users")

        conn.executemany(
            "INSERT INTO users (id, login, display_name, role) VALUES (?, ?, ?, ?)",
            SEED_USERS,
        )
        conn.executemany(
            "INSERT INTO rooms (id, name, building, floor, capacity, equipment) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (rid, name, building, floor, capacity, json.dumps(equipment, ensure_ascii=False))
                for rid, name, building, floor, capacity, equipment in SEED_ROOMS
            ],
        )
        conn.executemany(
            "INSERT INTO bookings "
            "(id, room_id, user_id, date, start_time, end_time, status, comment) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    bid,
                    room_id,
                    user_id,
                    (base_date + timedelta(days=offset)).isoformat(),
                    start_time,
                    end_time,
                    status,
                    comment,
                )
                for bid, room_id, user_id, offset, start_time, end_time, status, comment in SEED_BOOKINGS
            ],
        )
    return True


def seed_if_empty(conn: sqlite3.Connection | None = None) -> bool:
    """Создаёт схему и загружает seed, если таблица users пуста."""
    owns_conn = conn is None
    target = conn or get_connection()
    try:
        init_db(target)
        return seed_data(target, force=False)
    finally:
        if owns_conn:
            target.close()


def reset_seed(conn: sqlite3.Connection | None = None) -> bool:
    """Очищает таблицы и загружает свежий seed от текущей даты."""
    owns_conn = conn is None
    target = conn or get_connection()
    try:
        init_db(target)
        return seed_data(target, force=True)
    finally:
        if owns_conn:
            target.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Заполнение SQLite-базы seed-данными.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Очистить таблицы и перезалить seed с актуальными датами.",
    )
    args = parser.parse_args()
    if args.reset:
        reset_seed()
        print("Database reset and seeded.")
    else:
        inserted = seed_if_empty()
        print("Database seeded." if inserted else "Database already populated; skipped.")


if __name__ == "__main__":
    main()
