import pytest
from fastapi.testclient import TestClient

from tests.conftest import DAY_AFTER, TODAY, TOMORROW, YESTERDAY, assert_error, auth_headers


def test_free_slots_room1_tomorrow_seeded(client: TestClient):
    # В комнате 1 на завтра активные брони 10:00–11:30 и 14:00–15:30
    resp = client.get("/api/rooms/1/free-slots", params={"date": TOMORROW})
    assert resp.status_code == 200
    assert resp.json() == {
        "roomId": 1,
        "date": TOMORROW,
        "freeSlots": [
            {"startTime": "09:00", "endTime": "10:00"},
            {"startTime": "11:30", "endTime": "14:00"},
            {"startTime": "15:30", "endTime": "18:00"},
        ],
    }


def test_free_slots_ignores_cancelled_booking(client: TestClient):
    # В комнате 1 на сегодня есть только отменённая бронь 15:00–16:00
    resp = client.get("/api/rooms/1/free-slots", params={"date": TODAY})
    assert resp.status_code == 200
    assert resp.json()["freeSlots"] == [{"startTime": "09:00", "endTime": "18:00"}]


def test_free_slots_completely_free_room(client: TestClient):
    resp = client.get("/api/rooms/2/free-slots", params={"date": TOMORROW})
    assert resp.status_code == 200
    assert resp.json()["freeSlots"] == [{"startTime": "09:00", "endTime": "18:00"}]


def test_free_slots_adjacent_bookings_no_zero_length_slot(client: TestClient):
    headers = auth_headers("student1")
    r1 = client.post(
        "/api/bookings",
        headers=headers,
        json={"roomId": 2, "date": TOMORROW, "startTime": "10:00", "endTime": "11:00"},
    )
    r2 = client.post(
        "/api/bookings",
        headers=headers,
        json={"roomId": 2, "date": TOMORROW, "startTime": "11:00", "endTime": "12:00"},
    )
    assert r1.status_code == 201 and r2.status_code == 201

    resp = client.get("/api/rooms/2/free-slots", params={"date": TOMORROW})
    assert resp.status_code == 200
    assert resp.json()["freeSlots"] == [
        {"startTime": "09:00", "endTime": "10:00"},
        {"startTime": "12:00", "endTime": "18:00"},
    ]


def test_free_slots_fully_booked_day_returns_empty_list(client: TestClient):
    r = client.post(
        "/api/bookings",
        headers=auth_headers("student1"),
        json={"roomId": 3, "date": TOMORROW, "startTime": "09:00", "endTime": "18:00"},
    )
    assert r.status_code == 201

    resp = client.get("/api/rooms/3/free-slots", params={"date": TOMORROW})
    assert resp.status_code == 200
    assert resp.json()["freeSlots"] == []


def test_free_slots_bookings_on_edges(client: TestClient):
    headers = auth_headers("student1")
    assert (
        client.post(
            "/api/bookings",
            headers=headers,
            json={"roomId": 6, "date": TOMORROW, "startTime": "09:00", "endTime": "10:30"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/bookings",
            headers=headers,
            json={"roomId": 6, "date": TOMORROW, "startTime": "16:30", "endTime": "18:00"},
        ).status_code
        == 201
    )

    resp = client.get("/api/rooms/6/free-slots", params={"date": TOMORROW})
    assert resp.status_code == 200
    assert resp.json()["freeSlots"] == [{"startTime": "10:30", "endTime": "16:30"}]


def test_free_slots_past_date(client: TestClient):
    resp = client.get("/api/rooms/1/free-slots", params={"date": YESTERDAY})
    assert_error(resp, 400, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"date": "2025-13-01"},
        {"date": "12.11.2025"},
        {"date": "invalid"},
    ],
)
def test_free_slots_missing_or_invalid_date(client: TestClient, params):
    resp = client.get("/api/rooms/1/free-slots", params=params)
    assert_error(resp, 400, "VALIDATION_ERROR")


def test_free_slots_room_not_found(client: TestClient):
    resp = client.get("/api/rooms/999/free-slots", params={"date": TOMORROW})
    assert_error(resp, 404, "ROOM_NOT_FOUND")


def test_free_slots_lifecycle_create_and_cancel(client: TestClient):
    headers = auth_headers("student2")
    created = client.post(
        "/api/bookings",
        headers=headers,
        json={"roomId": 8, "date": DAY_AFTER, "startTime": "12:00", "endTime": "14:00"},
    )
    assert created.status_code == 201
    booking_id = created.json()["id"]

    slots_busy = client.get("/api/rooms/8/free-slots", params={"date": DAY_AFTER}).json()[
        "freeSlots"
    ]
    assert slots_busy == [
        {"startTime": "09:00", "endTime": "12:00"},
        {"startTime": "14:00", "endTime": "18:00"},
    ]

    cancelled = client.delete(f"/api/bookings/{booking_id}", headers=headers)
    assert cancelled.status_code == 200

    slots_freed = client.get("/api/rooms/8/free-slots", params={"date": DAY_AFTER}).json()[
        "freeSlots"
    ]
    assert slots_freed == [{"startTime": "09:00", "endTime": "18:00"}]
