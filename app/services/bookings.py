import sqlite3
from typing import Any

from app.db import transaction
from app.errors import (
    already_cancelled_error,
    booking_conflict_error,
    booking_not_found_error,
    forbidden_error,
    room_not_found_error,
    validation_error,
)
from app.repositories.bookings import (
    cancel_booking,
    get_booking_by_id,
    insert_booking,
    list_active_intervals_for_room_date,
)
from app.repositories.rooms import get_room_by_id
from app.validation import (
    intervals_overlap,
    parse_positive_int_value,
    validate_date_str,
    validate_time_slot,
)


def _hhmm_to_minutes(hhmm: str) -> int:
    hours_str, mins_str = hhmm.split(":")
    return int(hours_str) * 60 + int(mins_str)


def create_booking(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    payload: Any,
) -> dict[str, Any]:
    """Проверяет поля, существование аудитории и атомарно создаёт бронь без накладок."""
    if not isinstance(payload, dict):
        raise validation_error("Тело запроса должно быть JSON-объектом")

    required_fields = ("roomId", "date", "startTime", "endTime")
    missing = [f for f in required_fields if f not in payload]
    if missing:
        raise validation_error("Отсутствуют обязательные поля", {"missing": missing})

    room_id = parse_positive_int_value(payload["roomId"], "roomId")
    date_str = validate_date_str(payload["date"], allow_past=False, field="date")
    start_str = payload["startTime"]
    end_str = payload["endTime"]
    start_min, end_min = validate_time_slot(date_str, start_str, end_str)

    comment_raw = payload.get("comment")
    if comment_raw is None:
        comment = ""
    elif isinstance(comment_raw, str):
        comment = comment_raw
    else:
        raise validation_error("Поле comment должно быть строкой", {"comment": comment_raw})

    if get_room_by_id(conn, room_id) is None:
        raise room_not_found_error(room_id)

    with transaction(conn, immediate=True):
        existing_intervals = list_active_intervals_for_room_date(conn, room_id, date_str)
        for ex_start_str, ex_end_str in existing_intervals:
            ex_start = _hhmm_to_minutes(ex_start_str)
            ex_end = _hhmm_to_minutes(ex_end_str)
            if intervals_overlap(start_min, end_min, ex_start, ex_end):
                raise booking_conflict_error(room_id, date_str, start_str, end_str)

        booking_id = insert_booking(
            conn,
            room_id=room_id,
            user_id=user_id,
            date_str=date_str,
            start_time=start_str,
            end_time=end_str,
            comment=comment,
        )

    created = get_booking_by_id(conn, booking_id)
    if created is None:
        raise booking_not_found_error(booking_id)
    return created


def cancel_user_booking(
    conn: sqlite3.Connection,
    *,
    booking_id: int,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    """Отмена собственной брони; чужие отклоняются с 403 даже для администратора."""
    with transaction(conn, immediate=True):
        booking = get_booking_by_id(conn, booking_id)
        if booking is None:
            raise booking_not_found_error(booking_id)
        if booking["userId"] != current_user["id"]:
            raise forbidden_error(
                "Можно отменять только собственные бронирования",
                {"bookingId": booking_id},
            )
        if booking["status"] == "cancelled":
            raise already_cancelled_error(booking_id)
        cancel_booking(conn, booking_id)

    return {"id": booking_id, "status": "cancelled"}


def cancel_admin_booking(
    conn: sqlite3.Connection,
    *,
    booking_id: int,
) -> dict[str, Any]:
    """Отмена любой брони от имени администратора."""
    with transaction(conn, immediate=True):
        booking = get_booking_by_id(conn, booking_id)
        if booking is None:
            raise booking_not_found_error(booking_id)
        if booking["status"] == "cancelled":
            raise already_cancelled_error(booking_id)
        cancel_booking(conn, booking_id)

    return {"id": booking_id, "status": "cancelled"}
