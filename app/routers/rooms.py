import sqlite3
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.auth import get_db_conn
from app.errors import room_not_found_error, validation_error
from app.repositories.bookings import (
    list_active_intervals_by_date,
    list_active_intervals_for_room_date,
)
from app.repositories.rooms import get_room_by_id, list_rooms
from app.schemas import FreeSlotsResponse, RoomSchema
from app.services.slots import compute_free_slots
from app.validation import (
    intervals_overlap,
    parse_positive_int_query,
    validate_building,
    validate_date_str,
    validate_equipment_query,
    validate_time_slot,
)

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


def _hhmm_to_minutes(hhmm: str) -> int:
    hours_str, mins_str = hhmm.split(":")
    return int(hours_str) * 60 + int(mins_str)


def _parse_room_filters(
    building: str | None,
    min_capacity: str | None,
    equipment: str | None,
) -> tuple[str | None, int | None, list[str] | None]:
    valid_building = validate_building(building) if building is not None else None
    valid_capacity = (
        parse_positive_int_query(min_capacity, "minCapacity")
        if min_capacity is not None
        else None
    )
    valid_equipment = validate_equipment_query(equipment) if equipment is not None else None
    return valid_building, valid_capacity, valid_equipment


@router.get("", response_model=list[RoomSchema])
def get_rooms(
    building: str | None = Query(default=None),
    minCapacity: str | None = Query(default=None),
    equipment: str | None = Query(default=None),
    conn: sqlite3.Connection = Depends(get_db_conn),
) -> list[dict[str, Any]]:
    """Список аудиторий с фильтрами по корпусу, вместимости и оборудованию."""
    valid_building, valid_capacity, valid_equipment = _parse_room_filters(
        building, minCapacity, equipment
    )
    return list_rooms(
        conn,
        building=valid_building,
        min_capacity=valid_capacity,
        required_equipment=valid_equipment,
    )


@router.get("/available", response_model=list[RoomSchema])
def get_available_rooms(
    date: str | None = Query(default=None),
    startTime: str | None = Query(default=None),
    endTime: str | None = Query(default=None),
    building: str | None = Query(default=None),
    minCapacity: str | None = Query(default=None),
    equipment: str | None = Query(default=None),
    conn: sqlite3.Connection = Depends(get_db_conn),
) -> list[dict[str, Any]]:
    """Бонусный эндпоинт: ищет свободные аудитории на дату (и при желании на конкретное окно)."""
    if date is None:
        raise validation_error("Параметр date обязателен", {"field": "date"})
    date_str = validate_date_str(date, allow_past=False, field="date")

    if (startTime is None) != (endTime is None):
        raise validation_error(
            "Необходимо указать оба параметра: startTime и endTime",
            {"startTime": startTime, "endTime": endTime},
        )

    slot_range: tuple[int, int] | None = None
    if startTime is not None and endTime is not None:
        slot_range = validate_time_slot(date_str, startTime, endTime)

    valid_building, valid_capacity, valid_equipment = _parse_room_filters(
        building, minCapacity, equipment
    )
    candidate_rooms = list_rooms(
        conn,
        building=valid_building,
        min_capacity=valid_capacity,
        required_equipment=valid_equipment,
    )

    intervals_by_room = list_active_intervals_by_date(conn, date_str)
    available: list[dict[str, Any]] = []
    for room in candidate_rooms:
        room_intervals = intervals_by_room.get(room["id"], [])
        if slot_range is not None:
            req_start, req_end = slot_range
            has_conflict = any(
                intervals_overlap(
                    req_start,
                    req_end,
                    _hhmm_to_minutes(ex_start),
                    _hhmm_to_minutes(ex_end),
                )
                for ex_start, ex_end in room_intervals
            )
            if not has_conflict:
                available.append(room)
        elif compute_free_slots(room_intervals):
            available.append(room)

    return available


@router.get("/{room_id}", response_model=RoomSchema)
def get_room(
    room_id: int,
    conn: sqlite3.Connection = Depends(get_db_conn),
) -> dict[str, Any]:
    room = get_room_by_id(conn, room_id)
    if room is None:
        raise room_not_found_error(room_id)
    return room


@router.get("/{room_id}/free-slots", response_model=FreeSlotsResponse)
def get_room_free_slots(
    room_id: int,
    date: str | None = Query(default=None),
    conn: sqlite3.Connection = Depends(get_db_conn),
) -> dict[str, Any]:
    """Возвращает свободные 30-минутные интервалы аудитории на выбранную дату."""
    if get_room_by_id(conn, room_id) is None:
        raise room_not_found_error(room_id)

    if date is None:
        raise validation_error("Параметр date обязателен", {"field": "date"})
    date_str = validate_date_str(date, allow_past=False, field="date")

    intervals = list_active_intervals_for_room_date(conn, room_id, date_str)
    return {
        "roomId": room_id,
        "date": date_str,
        "freeSlots": compute_free_slots(intervals),
    }
