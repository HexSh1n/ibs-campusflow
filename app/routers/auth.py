import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, Request

from app.auth import get_db_conn, make_token
from app.errors import unauthorized_error, validation_error
from app.repositories.users import get_user_by_login
from app.routers.utils import read_json_body
from app.schemas import LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    conn: sqlite3.Connection = Depends(get_db_conn),
) -> dict[str, Any]:
    """Mock-авторизация: пароль совпадает с логином, выдаёт bearer-токен."""
    payload = await read_json_body(request)
    if not isinstance(payload, dict):
        raise validation_error("Тело запроса должно быть JSON-объектом")

    missing = [f for f in ("login", "password") if f not in payload]
    if missing:
        raise validation_error("Отсутствуют обязательные поля", {"missing": missing})

    login_val = payload["login"]
    password_val = payload["password"]
    if not isinstance(login_val, str) or not isinstance(password_val, str):
        raise validation_error("Поля login и password должны быть строками")
    if not login_val.strip():
        raise validation_error("Поле login не может быть пустым", {"field": "login"})

    user = get_user_by_login(conn, login_val)
    if user is None or password_val != user["login"]:
        raise unauthorized_error("Неверный логин или пароль")

    return {
        "token": make_token(user["login"]),
        "user": user,
    }
