import json
from typing import Any

from fastapi import Request

from app.errors import validation_error


async def read_json_body(request: Request) -> Any:
    """Читает JSON из тела запроса и превращает битый/пустой JSON в 400 VALIDATION_ERROR."""
    raw = await request.body()
    if not raw or not raw.strip():
        raise validation_error("Тело запроса не может быть пустым")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise validation_error("Некорректный JSON в теле запроса") from exc
