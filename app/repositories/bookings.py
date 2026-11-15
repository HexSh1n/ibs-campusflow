import sqlite3
from typing import Any

_BOOKING_SELECT = """
SELECT
    b.id,
    b.room_id,
    r.name AS room_name,
    b.user_id,
    u.display_name AS user_display_name,
    b.date,
    b.start_time,
    b.end_time,
    b.status,
    b.comment
FROM bookings b
JOIN rooms r ON r.id = b.room_id
JOIN users u ON u.id = b.user_id
"""


def _row_to_booking(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "roomId": row["room_id"],
        "roomName": row["room_name"],
        "userId": row["user_id"],
        "userDisplayName": row["user_display_name"],
        "date": row["date"],
        "startTime": row["start_time"],
        "endTime": row["end_time"],
        "status": row["status"],
        "comment": row["comment"],
    }


def get_booking_by_id(conn: sqlite3.Connection, booking_id: int) -> dict[str, Any] | None:
    row = conn.execute(_BOOKING_SELECT + " WHERE b.id = ?", (booking_id,)).fetchone()
    return _row_to_booking(row) if row is not None else None


def list_bookings(
    conn: sqlite3.Connection,
    *,
    user_id: int | None = None,
    room_id: int | None = None,
    date_str: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Выборка броней с опциональными фильтрами, отсортированная по id."""
    clauses: list[str] = []
    params: list[Any] = []
    if user_id is not None:
        clauses.append("b.user_id = ?")
        params.append(user_id)
    if room_id is not None:
        clauses.append("b.room_id = ?")
        params.append(room_id)
    if date_str is not None:
        clauses.append("b.date = ?")
        params.append(date_str)
    if status is not None:
        clauses.append("b.status = ?")
        params.append(status)

    sql = _BOOKING_SELECT
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY b.id ASC"

    rows = conn.execute(sql, params).fetchall()
    return [_row_to_booking(r) for r in rows]


def list_active_intervals_for_room_date(
    conn: sqlite3.Connection,
    room_id: int,
    date_str: str,
) -> list[tuple[str, str]]:
    """Активные занятые интервалы для конкретной аудитории на дату."""
    rows = conn.execute(
        "SELECT start_time, end_time FROM bookings "
        "WHERE room_id = ? AND date = ? AND status = 'active' "
        "ORDER BY start_time ASC, end_time ASC",
        (room_id, date_str),
    ).fetchall()
    return [(row["start_time"], row["end_time"]) for row in rows]


def list_active_intervals_by_date(
    conn: sqlite3.Connection,
    date_str: str,
) -> dict[int, list[tuple[str, str]]]:
    """Все активные интервалы за дату, сгруппированные по room_id."""
    rows = conn.execute(
        "SELECT room_id, start_time, end_time FROM bookings "
        "WHERE date = ? AND status = 'active' "
        "ORDER BY room_id ASC, start_time ASC, end_time ASC",
        (date_str,),
    ).fetchall()
    result: dict[int, list[tuple[str, str]]] = {}
    for row in rows:
        result.setdefault(row["room_id"], []).append((row["start_time"], row["end_time"]))
    return result


def insert_booking(
    conn: sqlite3.Connection,
    *,
    room_id: int,
    user_id: int,
    date_str: str,
    start_time: str,
    end_time: str,
    comment: str,
) -> int:
    cur = conn.execute(
        "INSERT INTO bookings "
        "(room_id, user_id, date, start_time, end_time, status, comment) "
        "VALUES (?, ?, ?, ?, ?, 'active', ?)",
        (room_id, user_id, date_str, start_time, end_time, comment),
    )
    return int(cur.lastrowid)


def cancel_booking(conn: sqlite3.Connection, booking_id: int) -> None:
    conn.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
