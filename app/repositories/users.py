import sqlite3
from typing import Any


def _row_to_user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "login": row["login"],
        "displayName": row["display_name"],
        "role": row["role"],
    }


def get_user_by_login(conn: sqlite3.Connection, login: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, login, display_name, role FROM users WHERE login = ?",
        (login,),
    ).fetchone()
    return _row_to_user(row) if row is not None else None


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT id, login, display_name, role FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return _row_to_user(row) if row is not None else None
