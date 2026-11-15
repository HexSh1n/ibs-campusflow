import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException


class Utf8JSONResponse(Response):
    """JSON-ответ без экранирования кириллицы и с явным charset=utf-8."""

    media_type = "application/json; charset=utf-8"

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")


class ApiError(Exception):
    """Ошибка API, которая сериализуется в единый формат {code, message, details}."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details if details is not None else {}

    def to_payload(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


def validation_error(message: str, details: dict[str, Any] | None = None) -> ApiError:
    return ApiError(400, "VALIDATION_ERROR", message, details)


def unauthorized_error(
    message: str = "Требуется авторизация",
    details: dict[str, Any] | None = None,
) -> ApiError:
    return ApiError(401, "UNAUTHORIZED", message, details)


def forbidden_error(
    message: str = "Доступ запрещён",
    details: dict[str, Any] | None = None,
) -> ApiError:
    return ApiError(403, "FORBIDDEN", message, details)


def room_not_found_error(room_id: Any) -> ApiError:
    return ApiError(404, "ROOM_NOT_FOUND", "Аудитория не найдена", {"roomId": room_id})


def booking_not_found_error(booking_id: Any) -> ApiError:
    return ApiError(
        404,
        "BOOKING_NOT_FOUND",
        "Бронирование не найдено",
        {"bookingId": booking_id},
    )


def booking_conflict_error(
    room_id: int,
    date_str: str,
    start_time: str,
    end_time: str,
) -> ApiError:
    return ApiError(
        409,
        "BOOKING_CONFLICT",
        "Аудитория уже забронирована на это время",
        {
            "roomId": room_id,
            "date": date_str,
            "startTime": start_time,
            "endTime": end_time,
        },
    )


def already_cancelled_error(booking_id: int) -> ApiError:
    return ApiError(
        409,
        "ALREADY_CANCELLED",
        "Бронирование уже отменено",
        {"bookingId": booking_id},
    )


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> Utf8JSONResponse:
    return Utf8JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "details": details if details is not None else {},
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Подключает единый обработчик ошибок для всего приложения."""

    @app.exception_handler(ApiError)
    async def handle_api_error(_request: Request, exc: ApiError) -> Utf8JSONResponse:
        return Utf8JSONResponse(status_code=exc.status_code, content=exc.to_payload())

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> Utf8JSONResponse:
        fields: list[dict[str, Any]] = []
        for err in exc.errors():
            loc = [str(part) for part in err.get("loc", []) if part != "body"]
            fields.append(
                {
                    "field": ".".join(loc) if loc else "body",
                    "error": err.get("msg", "Некорректное значение"),
                }
            )
        return _error_response(
            400,
            "VALIDATION_ERROR",
            "Ошибка валидации входных данных",
            {"errors": fields},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        _request: Request, exc: StarletteHTTPException
    ) -> Utf8JSONResponse:
        status_map = {
            400: ("VALIDATION_ERROR", "Ошибка валидации запроса"),
            401: ("UNAUTHORIZED", "Требуется авторизация"),
            403: ("FORBIDDEN", "Доступ запрещён"),
            404: ("NOT_FOUND", "Ресурс не найден"),
            405: ("METHOD_NOT_ALLOWED", "Метод не поддерживается"),
            409: ("CONFLICT", "Конфликт состояния"),
        }
        code, default_msg = status_map.get(
            exc.status_code, ("HTTP_ERROR", "Ошибка обработки запроса")
        )
        message = str(exc.detail) if exc.detail else default_msg
        return _error_response(exc.status_code, code, message, {})

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, _exc: Exception) -> Utf8JSONResponse:
        return _error_response(500, "INTERNAL_ERROR", "Внутренняя ошибка сервера", {})
