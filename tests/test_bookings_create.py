from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import clock
from tests.conftest import DAY_AFTER, TODAY, TOMORROW, YESTERDAY, assert_error, auth_headers


def test_create_booking_success(client: TestClient):
    resp = client.post(
        "/api/bookings",
        headers=auth_headers("student1"),
        json={
            "roomId": 2,
            "date": TOMORROW,
            "startTime": "10:00",
            "endTime": "11:30",
            "comment": "Семинар",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["roomId"] == 2
    assert body["roomName"] == "A-102"
    assert body["userId"] == 1
    assert body["userDisplayName"] == "Иван Студентов"
    assert body["date"] == TOMORROW
    assert body["startTime"] == "10:00"
    assert body["endTime"] == "11:30"
    assert body["status"] == "active"
    assert body["comment"] == "Семинар"
    assert isinstance(body["id"], int) and body["id"] > 0


def test_create_booking_ignores_user_id_in_body(client: TestClient):
    resp = client.post(
        "/api/bookings",
        headers=auth_headers("student1"),
        json={
            "roomId": 2,
            "userId": 2,
            "date": TOMORROW,
            "startTime": "10:00",
            "endTime": "11:00",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["userId"] == 1
    assert resp.json()["userDisplayName"] == "Иван Студентов"


def test_create_booking_requires_auth(client: TestClient):
    resp = client.post(
        "/api/bookings",
        json={
            "roomId": 2,
            "date": TOMORROW,
            "startTime": "10:00",
            "endTime": "11:00",
        },
    )
    assert_error(resp, 401, "UNAUTHORIZED")


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [
        ("11:00", "11:00"),
        ("12:00", "11:00"),
        ("08:30", "09:30"),
        ("17:30", "18:30"),
        ("10:15", "11:00"),
        ("10:00", "10:45"),
        ("9:00", "10:00"),
        ("25:00", "26:00"),
        ("10:60", "11:00"),
        ("abc", "11:00"),
    ],
)
def test_create_booking_invalid_times(client: TestClient, start_time, end_time):
    resp = client.post(
        "/api/bookings",
        headers=auth_headers("student1"),
        json={
            "roomId": 2,
            "date": TOMORROW,
            "startTime": start_time,
            "endTime": end_time,
        },
    )
    assert_error(resp, 400, "VALIDATION_ERROR")


def test_create_booking_past_date(client: TestClient):
    resp = client.post(
        "/api/bookings",
        headers=auth_headers("student1"),
        json={
            "roomId": 2,
            "date": YESTERDAY,
            "startTime": "10:00",
            "endTime": "11:00",
        },
    )
    assert_error(resp, 400, "VALIDATION_ERROR")


def test_create_booking_today_past_time_returns_400(client: TestClient):
    with clock.frozen_clock(datetime(2025, 11, 12, 14, 15, 0)):
        resp_past = client.post(
            "/api/bookings",
            headers=auth_headers("student1"),
            json={
                "roomId": 2,
                "date": TODAY,
                "startTime": "14:00",
                "endTime": "15:00",
            },
        )
        assert_error(resp_past, 400, "VALIDATION_ERROR")

        resp_future = client.post(
            "/api/bookings",
            headers=auth_headers("student1"),
            json={
                "roomId": 2,
                "date": TODAY,
                "startTime": "14:30",
                "endTime": "15:30",
            },
        )
        assert resp_future.status_code == 201


def test_create_booking_full_day_boundary_allowed(client: TestClient):
    resp = client.post(
        "/api/bookings",
        headers=auth_headers("student1"),
        json={
            "roomId": 2,
            "date": TOMORROW,
            "startTime": "09:00",
            "endTime": "18:00",
        },
    )
    assert resp.status_code == 201


@pytest.mark.parametrize("missing_field", ["roomId", "date", "startTime", "endTime"])
def test_create_booking_missing_required_field(client: TestClient, missing_field):
    payload = {
        "roomId": 2,
        "date": TOMORROW,
        "startTime": "10:00",
        "endTime": "11:00",
    }
    del payload[missing_field]
    resp = client.post("/api/bookings", headers=auth_headers("student1"), json=payload)
    assert_error(resp, 400, "VALIDATION_ERROR")


def test_create_booking_room_not_found(client: TestClient):
    resp = client.post(
        "/api/bookings",
        headers=auth_headers("student1"),
        json={
            "roomId": 999,
            "date": TOMORROW,
            "startTime": "10:00",
            "endTime": "11:00",
        },
    )
    assert_error(resp, 404, "ROOM_NOT_FOUND")


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [
        ("10:30", "11:00"),  # внутри существующей 10:00–11:30
        ("09:30", "12:00"),  # полностью накрывает существующую
        ("09:30", "10:30"),  # пересечение слева
        ("11:00", "12:00"),  # пересечение справа
        ("10:00", "11:30"),  # точное совпадение
    ],
)
def test_create_booking_conflict_cases(client: TestClient, start_time, end_time):
    resp = client.post(
        "/api/bookings",
        headers=auth_headers("student2"),
        json={
            "roomId": 1,
            "date": TOMORROW,
            "startTime": start_time,
            "endTime": end_time,
        },
    )
    body = assert_error(resp, 409, "BOOKING_CONFLICT")
    assert body["details"] == {
        "roomId": 1,
        "date": TOMORROW,
        "startTime": start_time,
        "endTime": end_time,
    }


def test_create_booking_touching_boundaries_allowed(client: TestClient):
    r1 = client.post(
        "/api/bookings",
        headers=auth_headers("student2"),
        json={"roomId": 1, "date": TOMORROW, "startTime": "11:30", "endTime": "14:00"},
    )
    assert r1.status_code == 201


def test_create_booking_over_cancelled_allowed(client: TestClient):
    # В комнате 1 на сегодня отменённая бронь 15:00–16:00 — слот должен быть свободен
    resp = client.post(
        "/api/bookings",
        headers=auth_headers("student2"),
        json={"roomId": 1, "date": TODAY, "startTime": "15:00", "endTime": "16:00"},
    )
    assert resp.status_code == 201


def test_create_booking_same_time_different_room_or_date_allowed(client: TestClient):
    headers = auth_headers("student2")
    r_other_room = client.post(
        "/api/bookings",
        headers=headers,
        json={"roomId": 2, "date": TOMORROW, "startTime": "10:00", "endTime": "11:30"},
    )
    r_other_date = client.post(
        "/api/bookings",
        headers=headers,
        json={"roomId": 1, "date": DAY_AFTER, "startTime": "10:00", "endTime": "11:30"},
    )
    assert r_other_room.status_code == 201
    assert r_other_date.status_code == 201


def test_create_booking_comment_optional(client: TestClient):
    resp = client.post(
        "/api/bookings",
        headers=auth_headers("student1"),
        json={"roomId": 2, "date": TOMORROW, "startTime": "12:00", "endTime": "13:00"},
    )
    assert resp.status_code == 201
    assert resp.json()["comment"] == ""


@pytest.mark.parametrize("room_id", ["1", True, 0, -5, 1.5, None])
def test_create_booking_invalid_room_id_type_or_value(client: TestClient, room_id):
    resp = client.post(
        "/api/bookings",
        headers=auth_headers("student1"),
        json={
            "roomId": room_id,
            "date": TOMORROW,
            "startTime": "12:00",
            "endTime": "13:00",
        },
    )
    assert_error(resp, 400, "VALIDATION_ERROR")


def test_create_booking_invalid_json_and_comment_type(client: TestClient):
    resp_bad_json = client.post(
        "/api/bookings",
        headers={**auth_headers("student1"), "Content-Type": "application/json"},
        content=b"not-json",
    )
    assert_error(resp_bad_json, 400, "VALIDATION_ERROR")

    resp_bad_comment = client.post(
        "/api/bookings",
        headers=auth_headers("student1"),
        json={
            "roomId": 2,
            "date": TOMORROW,
            "startTime": "12:00",
            "endTime": "13:00",
            "comment": 123,
        },
    )
    assert_error(resp_bad_comment, 400, "VALIDATION_ERROR")
