from datetime import datetime

import pytest

from app import clock
from app.errors import ApiError
from app.services.slots import compute_free_slots
from app.validation import (
    intervals_overlap,
    parse_time_minutes,
    validate_date_str,
    validate_time_slot,
)


@pytest.mark.parametrize(
    ("intervals", "expected"),
    [
        ([], [{"startTime": "09:00", "endTime": "18:00"}]),
        (
            [("10:00", "11:30"), ("14:00", "15:30")],
            [
                {"startTime": "09:00", "endTime": "10:00"},
                {"startTime": "11:30", "endTime": "14:00"},
                {"startTime": "15:30", "endTime": "18:00"},
            ],
        ),
        (
            [("10:00", "11:00"), ("11:00", "12:00")],
            [
                {"startTime": "09:00", "endTime": "10:00"},
                {"startTime": "12:00", "endTime": "18:00"},
            ],
        ),
        (
            [("10:00", "12:00"), ("11:00", "13:00")],
            [
                {"startTime": "09:00", "endTime": "10:00"},
                {"startTime": "13:00", "endTime": "18:00"},
            ],
        ),
        (
            [("09:00", "12:00"), ("12:00", "18:00")],
            [],
        ),
        (
            [("09:00", "10:00"), ("17:00", "18:00")],
            [{"startTime": "10:00", "endTime": "17:00"}],
        ),
        (
            [("08:00", "10:00"), ("17:30", "19:00")],
            [{"startTime": "10:00", "endTime": "17:30"}],
        ),
    ],
)
def test_compute_free_slots_cases(intervals, expected):
    assert compute_free_slots(intervals) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("00:00", 0), ("09:00", 540), ("14:30", 870), ("18:00", 1080), ("23:30", 1410)],
)
def test_parse_time_minutes_valid(raw, expected):
    assert parse_time_minutes(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["9:00", "09:15", "10:45", "24:00", "25:00", "10:60", "abc", "", None, 900],
)
def test_parse_time_minutes_invalid(raw):
    with pytest.raises(ApiError) as exc_info:
        parse_time_minutes(raw)
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "VALIDATION_ERROR"


def test_validate_date_str(frozen_today):
    assert validate_date_str("2025-11-12") == "2025-11-12"
    assert validate_date_str("2025-11-11", allow_past=True) == "2025-11-11"
    with pytest.raises(ApiError) as exc:
        validate_date_str("2025-11-11")
    assert exc.value.code == "VALIDATION_ERROR"

    for bad in ["2025-13-01", "12.11.2025", "2025-11-1", "invalid", None]:
        with pytest.raises(ApiError):
            validate_date_str(bad)


def test_intervals_overlap():
    # Касание границ конфликтом не считается
    assert intervals_overlap(600, 690, 690, 750) is False
    assert intervals_overlap(690, 750, 600, 690) is False
    # Пересечение есть
    assert intervals_overlap(600, 690, 660, 720) is True
    assert intervals_overlap(600, 750, 630, 690) is True
    assert intervals_overlap(600, 690, 600, 690) is True


def test_validate_time_slot_today_past_time(frozen_today):
    with clock.frozen_clock(datetime(2025, 11, 12, 13, 15, 0)):
        # 13:00 < 13:15 — уже прошло
        with pytest.raises(ApiError) as exc:
            validate_time_slot("2025-11-12", "13:00", "14:00")
        assert exc.value.status_code == 400
        assert exc.value.code == "VALIDATION_ERROR"

        # 13:30 >= 13:15 — ещё можно
        assert validate_time_slot("2025-11-12", "13:30", "14:30") == (810, 870)

    # Ровно 14:00 при старте в 14:00 разрешено
    with clock.frozen_clock(datetime(2025, 11, 12, 14, 0, 0)):
        assert validate_time_slot("2025-11-12", "14:00", "15:00") == (840, 900)
