import sqlite3
from typing import Any, Iterator

from fastapi import Depends, Request

from app.db import get_connection
from app.errors import forbidden_error, unauthorized_error
from app.repositories.users import get_user_by_login

TOKEN_PREFIX = "mock-token-"


def make_token(login: str) -> str:
    return f"{TOKEN_PREFIX}{login}"


def get_db_conn() -> Iterator[sqlite3.Connection]:
    """Открывает соединение с БД на время HTTP-запроса и закрывает его в конце."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def get_current_user(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db_conn),
) -> dict[str, Any]:
    """Достаёт пользователя по заголовку Authorization: Bearer mock-token-<login>."""
    auth_header = request.headers.get("authorization")
    if not auth_header:
        raise unauthorized_error("Отсутствует заголовок Authorization")

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0] != "Bearer" or not parts[1].strip():
        raise unauthorized_error("Некорректный формат заголовка Authorization")

    token = parts[1].strip()
    if not token.startswith(TOKEN_PREFIX):
        raise unauthorized_error("Недействительный токен авторизации")

    login = token[len(TOKEN_PREFIX) :]
    if not login:
        raise unauthorized_error("Недействительный токен авторизации")

    user = get_user_by_login(conn, login)
    if user is None:
        raise unauthorized_error("Недействительный токен авторизации")

    return user


def require_admin(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Проверяет, что текущий пользователь — администратор."""
    if current_user["role"] != "admin":
        raise forbidden_error("Доступ разрешён только администраторам")
    return current_user
