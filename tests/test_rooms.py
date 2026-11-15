from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import clock
from tests.conftest import TODAY, TOMORROW, YESTERDAY, assert_error, auth_headers


def test_list_rooms_all(client: TestClient):
    resp = client.get("/api/rooms")
    assert resp.status_code == 200
    rooms = resp.json()
    assert len(rooms) == 12
    first = rooms[0]
    assert set(first.keys()) == {"id", "name", "building", "floor", "capacity", "equipment"}
    assert first == {
        "id": 1,
        "name": "A-101",
        "building": "A",
        "floor": 1,
        "capacity": 30,
        "equipment": ["projector", "whiteboard"],
    }


def test_filter_rooms_by_building(client: TestClient):
    resp = client.get("/api/rooms", params={"building": "B"})
    assert resp.status_code == 200
    assert [r["id"] for r in resp.json()] == [4, 5, 6]


def test_filter_rooms_by_min_capacity(client: TestClient):
    resp = client.get("/api/rooms", params={"minCapacity": "40"})
    assert resp.status_code == 200
    assert [r["id"] for r in resp.json()] == [4, 7, 10]


def test_filter_rooms_by_equipment_all_required(client: TestClient):
    resp = client.get("/api/rooms", params={"equipment": "projector,whiteboard"})
    assert resp.status_code == 200
    assert [r["id"] for r in resp.json()] == [1, 5, 9]


def test_filter_rooms_combined(client: TestClient):
    resp = client.get(
        "/api/rooms",
        params={"building": "D", "minCapacity": "20", "equipment": "projector"},
    )
    assert resp.status_code == 200
    assert [r["id"] for r in resp.json()] == [10, 12]


@pytest.mark.parametrize(
    "params",
    [
        {"equipment": "laser"},
        {"equipment": "projector,"},
        {"equipment": ""},
        {"minCapacity": "0"},
        {"minCapacity": "-1"},
        {"minCapacity": "abc"},
        {"minCapacity": "1.5"},
        {"building": "Z"},
    ],
)
def test_filter_rooms_validation_errors(client: TestClient, params):
    resp = client.get("/api/rooms", params=params)
    assert_error(resp, 400, "VALIDATION_ERROR")


def test_get_room_by_id_success(client: TestClient):
    resp = client.get("/api/rooms/1")
    assert resp.status_code == 200
    assert resp.json()["name"] == "A-101"


def test_get_room_by_id_not_found(client: TestClient):
    resp = client.get("/api/rooms/999")
    assert_error(resp, 404, "ROOM_NOT_FOUND")


def test_available_rooms_with_time_window_excludes_busy_room(client: TestClient):
    # На завтра в комнате 1 активная бронь 10:00–11:30, в комнате 4 — 09:00–10:30
    resp = client.get(
        "/api/rooms/available",
        params={"date": TOMORROW, "startTime": "10:00", "endTime": "11:00"},
    )
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()]
    assert 1 not in ids
    assert 4 not in ids
    assert 2 in ids


def test_available_rooms_touching_boundaries_is_available(client: TestClient):
    # Комната 1 завтра занята 10:00–11:30 и 14:00–15:30; окно 11:30–14:00 свободно
    resp = client.get(
        "/api/rooms/available",
        params={
            "date": TOMORROW,
            "startTime": "11:30",
            "endTime": "14:00",
            "building": "A",
            "equipment": "projector,whiteboard",
        },
    )
    assert resp.status_code == 200
    assert [r["id"] for r in resp.json()] == [1]


def test_available_rooms_without_time_window_excludes_fully_booked(client: TestClient):
    r = client.post(
        "/api/bookings",
        headers=auth_headers("student1"),
        json={
            "roomId": 2,
            "date": TOMORROW,
            "startTime": "09:00",
            "endTime": "18:00",
        },
    )
    assert r.status_code == 201

    resp = client.get("/api/rooms/available", params={"date": TOMORROW, "building": "A"})
    assert resp.status_code == 200
    ids = [room["id"] for room in resp.json()]
    assert ids == [1, 3]


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"date": YESTERDAY},
        {"date": "bad-date"},
        {"date": TOMORROW, "startTime": "10:00"},
        {"date": TOMORROW, "endTime": "11:00"},
        {"date": TOMORROW, "startTime": "11:00", "endTime": "10:00"},
        {"date": TOMORROW, "startTime": "10:15", "endTime": "11:00"},
        {"date": TOMORROW, "building": "Z"},
    ],
)
def test_available_rooms_validation_errors(client: TestClient, params):
    resp = client.get("/api/rooms/available", params=params)
    assert_error(resp, 400, "VALIDATION_ERROR")


def test_available_rooms_today_past_time_rejected(client: TestClient):
    with clock.frozen_clock(datetime(2025, 11, 12, 12, 30, 0)):
        resp = client.get(
            "/api/rooms/available",
            params={"date": TODAY, "startTime": "12:00", "endTime": "13:00"},
        )
        assert_error(resp, 400, "VALIDATION_ERROR")
