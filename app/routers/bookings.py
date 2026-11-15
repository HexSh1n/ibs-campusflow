import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, Query, Request

from app.auth import get_current_user, get_db_conn
from app.repositories.bookings import list_bookings
from app.routers.utils import read_json_body
from app.schemas import BookingCancelResponse, BookingSchema
from app.services.bookings import cancel_user_booking, create_booking
from app.validation import validate_booking_status

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", status_code=201, response_model=BookingSchema)
async def post_booking(
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_conn),
) -> dict[str, Any]:
    """Создаёт бронь для авторизованного пользователя (userId берётся из токена)."""
    payload = await read_json_body(request)
    return create_booking(conn, user_id=current_user["id"], payload=payload)


@router.get("/my", response_model=list[BookingSchema])
def get_my_bookings(
    status: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_conn),
) -> list[dict[str, Any]]:
    valid_status = validate_booking_status(status) if status is not None else None
    return list_bookings(conn, user_id=current_user["id"], status=valid_status)


@router.delete("/{booking_id}", response_model=BookingCancelResponse)
def delete_my_booking(
    booking_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_conn),
) -> dict[str, Any]:
    return cancel_user_booking(
        conn,
        booking_id=booking_id,
        current_user=current_user,
    )
