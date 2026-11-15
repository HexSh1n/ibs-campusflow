import re
from datetime import date
from typing import Any

from app import clock
from app.errors import validation_error

VALID_BUILDINGS = ("A", "B", "C", "D")
VALID_EQUIPMENT = ("projector", "whiteboard", "computers", "audio", "video")
VALID_BOOKING_STATUSES = ("active", "cancelled")

WORK_DAY_START_MINUTES = 9 * 60
WORK_DAY_END_MINUTES = 18 * 60

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")
_INT_STR_RE = re.compile(r"^-?\d+$")


def is_strict_int(value: Any) -> bool:
    """В Python bool наследуется от int, поэтому проверяем отдельно."""
    return isinstance(value, int) and not isinstance(value, bool)


def parse_positive_int_value(value: Any, field: str) -> int:
    """Проверяет, что JSON-значение — целое положительное число (не bool и не строка)."""
    if not is_strict_int(value) or value <= 0:
        raise validation_error(
            f"Поле {field} должно быть целым положительным числом",
            {field: value},
        )
    return value


def parse_positive_int_query(raw: str, field: str) -> int:
    """Проверяет query-параметр на целое число > 0."""
    if not _INT_STR_RE.fullmatch(raw):
        raise validation_error(
            f"Параметр {field} должен быть целым числом больше 0",
            {field: raw},
        )
    parsed = int(raw)
    if parsed <= 0:
        raise validation_error(
            f"Параметр {field} должен быть больше 0",
            {field: raw},
        )
    return parsed


def validate_date_str(
    value: Any,
    *,
    allow_past: bool = False,
    field: str = "date",
) -> str:
    """Проверяет формат YYYY-MM-DD и при allow_past=False запрещает прошедшие даты."""
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise validation_error(
            "Некорректный формат даты, ожидается YYYY-MM-DD",
            {field: value},
        )
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise validation_error("Некорректная дата", {field: value}) from exc

    if not allow_past and parsed < clock.today():
        raise validation_error("Дата не может быть в прошлом", {field: value})
    return value


def parse_time_minutes(value: Any, *, field: str = "time") -> int:
    """Разбирает строку HH:MM (шаг 30 минут) и возвращает минуты от начала суток."""
    if not isinstance(value, str) or not _TIME_RE.fullmatch(value):
        raise validation_error(
            f"Некорректный формат времени в поле {field}, ожидается HH:MM",
            {field: value},
        )
    hours_str, mins_str = value.split(":")
    hours = int(hours_str)
    mins = int(mins_str)
    if hours > 23 or mins > 59:
        raise validation_error(f"Некорректное время в поле {field}", {field: value})

    total = hours * 60 + mins
    if total % 30 != 0:
        raise validation_error(
            f"Время в поле {field} должно быть кратно 30 минутам",
            {field: value},
        )
    return total


def format_minutes(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def validate_time_slot(
    date_str: str,
    start_value: Any,
    end_value: Any,
) -> tuple[int, int]:
    """Проверяет интервал: шаг 30 мин, порядок, рабочие часы 09:00–18:00 и текущее время на сегодня."""
    start_min = parse_time_minutes(start_value, field="startTime")
    end_min = parse_time_minutes(end_value, field="endTime")

    if start_min >= end_min:
        raise validation_error(
            "Время окончания должно быть строго больше времени начала",
            {"startTime": start_value, "endTime": end_value},
        )
    if start_min < WORK_DAY_START_MINUTES or end_min > WORK_DAY_END_MINUTES:
        raise validation_error(
            "Время бронирования должно находиться в интервале 09:00–18:00",
            {"startTime": start_value, "endTime": end_value},
        )

    if date.fromisoformat(date_str) == clock.today():
        current_dt = clock.now()
        current_minutes = current_dt.hour * 60 + current_dt.minute
        if start_min < current_minutes:
            raise validation_error(
                "Нельзя забронировать время, которое уже прошло",
                {"date": date_str, "startTime": start_value},
            )

    return start_min, end_min


def intervals_overlap(start_a: int, end_a: int, start_b: int, end_b: int) -> bool:
    """Пересечение полуинтервалов [start, end); касание границ конфликтом не считается."""
    return start_a < end_b and start_b < end_a


def validate_building(value: Any, *, field: str = "building") -> str:
    if not isinstance(value, str) or value not in VALID_BUILDINGS:
        raise validation_error(
            f"Поле {field} должно быть одним из: {', '.join(VALID_BUILDINGS)}",
            {field: value},
        )
    return value


def validate_equipment_query(raw: str) -> list[str]:
    """Разбирает query-параметр equipment (через запятую) и проверяет допустимые значения."""
    if not raw.strip():
        raise validation_error(
            "Параметр equipment не должен быть пустым",
            {"equipment": raw},
        )
    parts = [item.strip() for item in raw.split(",")]
    if any(not item for item in parts):
        raise validation_error(
            "Некорректный список оборудования в параметре equipment",
            {"equipment": raw},
        )
    result: list[str] = []
    for item in parts:
        if item not in VALID_EQUIPMENT:
            raise validation_error(
                f"Неизвестный тип оборудования: {item}",
                {"equipment": item, "allowed": list(VALID_EQUIPMENT)},
            )
        if item not in result:
            result.append(item)
    return result


def validate_booking_status(raw: str, *, field: str = "status") -> str:
    if raw not in VALID_BOOKING_STATUSES:
        raise validation_error(
            f"Некорректный статус: {raw}",
            {field: raw, "allowed": list(VALID_BOOKING_STATUSES)},
        )
    return raw


def validate_room_payload(data: Any) -> dict[str, Any]:
    """Проверяет тело запроса для создания/обновления аудитории (все поля обязательны)."""
    if not isinstance(data, dict):
        raise validation_error("Тело запроса должно быть JSON-объектом")

    required_fields = ("name", "building", "floor", "capacity", "equipment")
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise validation_error("Отсутствуют обязательные поля", {"missing": missing})

    name_raw = data["name"]
    if not isinstance(name_raw, str) or not name_raw.strip():
        raise validation_error("Поле name должно быть непустой строкой", {"name": name_raw})
    name = name_raw.strip()

    building = validate_building(data["building"])

    floor_raw = data["floor"]
    if not is_strict_int(floor_raw) or floor_raw < 1:
        raise validation_error(
            "Поле floor должно быть целым числом >= 1",
            {"floor": floor_raw},
        )

    capacity_raw = data["capacity"]
    if not is_strict_int(capacity_raw) or capacity_raw <= 0:
        raise validation_error(
            "Поле capacity должно быть целым числом > 0",
            {"capacity": capacity_raw},
        )

    eq_raw = data["equipment"]
    if not isinstance(eq_raw, list):
        raise validation_error(
            "Поле equipment должно быть массивом строк",
            {"equipment": eq_raw},
        )
    equipment: list[str] = []
    for item in eq_raw:
        if not isinstance(item, str) or item not in VALID_EQUIPMENT:
            raise validation_error(
                f"Неизвестный тип оборудования: {item}",
                {"equipment": item, "allowed": list(VALID_EQUIPMENT)},
            )
        if item not in equipment:
            equipment.append(item)

    return {
        "name": name,
        "building": building,
        "floor": floor_raw,
        "capacity": capacity_raw,
        "equipment": equipment,
    }
