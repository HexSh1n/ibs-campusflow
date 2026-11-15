import json
import sqlite3
from typing import Any


def _row_to_room(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "building": row["building"],
        "floor": row["floor"],
        "capacity": row["capacity"],
        "equipment": json.loads(row["equipment"]),
    }


def list_rooms(
    conn: sqlite3.Connection,
    *,
    building: str | None = None,
    min_capacity: int | None = None,
    required_equipment: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Возвращает аудитории с фильтрацией по корпусу, вместимости и оборудованию."""
    clauses: list[str] = []
    params: list[Any] = []
    if building is not None:
        clauses.append("building = ?")
        params.append(building)
    if min_capacity is not None:
        clauses.append("capacity >= ?")
        params.append(min_capacity)

    sql = "SELECT id, name, building, floor, capacity, equipment FROM rooms"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY id ASC"

    rows = conn.execute(sql, params).fetchall()
    rooms = [_row_to_room(r) for r in rows]
    if required_equipment:
        req_set = set(required_equipment)
        rooms = [room for room in rooms if req_set.issubset(room["equipment"])]
    return rooms


def get_room_by_id(conn: sqlite3.Connection, room_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, name, building, floor, capacity, equipment FROM rooms WHERE id = ?",
        (room_id,),
    ).fetchone()
    return _row_to_room(row) if row is not None else None


def get_room_by_name(conn: sqlite3.Connection, name: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, name, building, floor, capacity, equipment FROM rooms WHERE name = ?",
        (name,),
    ).fetchone()
    return _row_to_room(row) if row is not None else None


def create_room(conn: sqlite3.Connection, data: dict[str, Any]) -> dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO rooms (name, building, floor, capacity, equipment) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            data["name"],
            data["building"],
            data["floor"],
            data["capacity"],
            json.dumps(data["equipment"], ensure_ascii=False),
        ),
    )
    return {
        "id": int(cur.lastrowid),
        "name": data["name"],
        "building": data["building"],
        "floor": data["floor"],
        "capacity": data["capacity"],
        "equipment": list(data["equipment"]),
    }


def update_room(
    conn: sqlite3.Connection, room_id: int, data: dict[str, Any]
) -> dict[str, Any] | None:
    cur = conn.execute(
        "UPDATE rooms SET name = ?, building = ?, floor = ?, capacity = ?, equipment = ? "
        "WHERE id = ?",
        (
            data["name"],
            data["building"],
            data["floor"],
            data["capacity"],
            json.dumps(data["equipment"], ensure_ascii=False),
            room_id,
        ),
    )
    if cur.rowcount == 0:
        return None
    return get_room_by_id(conn, room_id)
