import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.auth import get_db_conn, require_admin
from app.db import transaction
from app.errors import room_not_found_error, validation_error
from app.repositories.bookings import list_bookings
from app.repositories.rooms import (
    create_room,
    get_room_by_id,
    get_room_by_name,
    update_room,
)
from app.routers.utils import read_json_body
from app.schemas import BookingCancelResponse, BookingSchema, RoomSchema
from app.services.bookings import cancel_admin_booking
from app.validation import (
    parse_positive_int_query,
    validate_booking_status,
    validate_date_str,
    validate_room_payload,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/bookings", response_model=list[BookingSchema])
def admin_list_bookings(
    date: str | None = Query(default=None),
    roomId: str | None = Query(default=None),
    userId: str | None = Query(default=None),
    status: str | None = Query(default=None),
    _admin: dict[str, Any] = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db_conn),
) -> list[dict[str, Any]]:
    """Все бронирования в системе с фильтрами по дате, комнате, пользователю и статусу."""
    valid_date = (
        validate_date_str(date, allow_past=True, field="date")
        if date is not None
        else None
    )
    valid_room_id = parse_positive_int_query(roomId, "roomId") if roomId is not None else None
    valid_user_id = parse_positive_int_query(userId, "userId") if userId is not None else None
    valid_status = validate_booking_status(status) if status is not None else None
    return list_bookings(
        conn,
        date_str=valid_date,
        room_id=valid_room_id,
        user_id=valid_user_id,
        status=valid_status,
    )


@router.delete("/bookings/{booking_id}", response_model=BookingCancelResponse)
def admin_delete_booking(
    booking_id: int,
    _admin: dict[str, Any] = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db_conn),
) -> dict[str, Any]:
    return cancel_admin_booking(conn, booking_id=booking_id)


@router.post("/rooms", status_code=201, response_model=RoomSchema)
async def admin_create_room(
    request: Request,
    _admin: dict[str, Any] = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db_conn),
) -> dict[str, Any]:
    payload = await read_json_body(request)
    valid = validate_room_payload(payload)

    with transaction(conn, immediate=True):
        if get_room_by_name(conn, valid["name"]) is not None:
            raise validation_error(
                "Аудитория с таким названием уже существует",
                {"field": "name", "name": valid["name"]},
            )
        return create_room(conn, valid)


@router.put("/rooms/{room_id}", response_model=RoomSchema)
async def admin_update_room(
    room_id: int,
    request: Request,
    _admin: dict[str, Any] = Depends(require_admin),
    conn: sqlite3.Connection = Depends(get_db_conn),
) -> dict[str, Any]:
    payload = await read_json_body(request)
    valid = validate_room_payload(payload)

    with transaction(conn, immediate=True):
        if get_room_by_id(conn, room_id) is None:
            raise room_not_found_error(room_id)
        existing_by_name = get_room_by_name(conn, valid["name"])
        if existing_by_name is not None and existing_by_name["id"] != room_id:
            raise validation_error(
                "Аудитория с таким названием уже существует",
                {"field": "name", "name": valid["name"]},
            )
        updated = update_room(conn, room_id, valid)
        if updated is None:
            raise room_not_found_error(room_id)
        return updated
