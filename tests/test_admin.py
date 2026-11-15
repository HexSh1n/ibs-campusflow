import pytest
from fastapi.testclient import TestClient

from tests.conftest import DAY_AFTER, TODAY, TOMORROW, assert_error, auth_headers


@pytest.mark.parametrize(
    ("method", "url", "body"),
    [
        ("GET", "/api/admin/bookings", None),
        ("DELETE", "/api/admin/bookings/1", None),
        (
            "POST",
            "/api/admin/rooms",
            {
                "name": "D-201",
                "building": "D",
                "floor": 2,
                "capacity": 25,
                "equipment": ["projector"],
            },
        ),
        (
            "PUT",
            "/api/admin/rooms/1",
            {
                "name": "A-101",
                "building": "A",
                "floor": 1,
                "capacity": 35,
                "equipment": ["projector"],
            },
        ),
    ],
)
def test_admin_endpoints_reject_student_and_unauthenticated(
    client: TestClient, method, url, body
):
    resp_no_auth = client.request(method, url, json=body)
    assert_error(resp_no_auth, 401, "UNAUTHORIZED")

    resp_student = client.request(
        method, url, headers=auth_headers("student1"), json=body
    )
    assert_error(resp_student, 403, "FORBIDDEN")


def test_admin_list_all_bookings(client: TestClient):
    resp = client.get("/api/admin/bookings", headers=auth_headers("admin"))
    assert resp.status_code == 200
    assert [b["id"] for b in resp.json()] == [1, 2, 3, 4, 5, 6, 7]


def test_admin_list_bookings_filters(client: TestClient):
    headers = auth_headers("admin")

    by_date = client.get("/api/admin/bookings", headers=headers, params={"date": DAY_AFTER})
    assert [b["id"] for b in by_date.json()] == [6]

    by_room = client.get("/api/admin/bookings", headers=headers, params={"roomId": "1"})
    assert [b["id"] for b in by_room.json()] == [1, 2, 5]

    by_user = client.get("/api/admin/bookings", headers=headers, params={"userId": "2"})
    assert [b["id"] for b in by_user.json()] == [2, 3, 6]

    by_status = client.get(
        "/api/admin/bookings", headers=headers, params={"status": "cancelled"}
    )
    assert [b["id"] for b in by_status.json()] == [5]

    combined = client.get(
        "/api/admin/bookings",
        headers=headers,
        params={"date": TOMORROW, "roomId": "1", "userId": "1", "status": "active"},
    )
    assert [b["id"] for b in combined.json()] == [1]

    today_only = client.get("/api/admin/bookings", headers=headers, params={"date": TODAY})
    assert [b["id"] for b in today_only.json()] == [5]


@pytest.mark.parametrize(
    "params",
    [
        {"date": "bad-date"},
        {"roomId": "0"},
        {"roomId": "abc"},
        {"userId": "-1"},
        {"status": "pending"},
    ],
)
def test_admin_list_bookings_invalid_filters(client: TestClient, params):
    resp = client.get("/api/admin/bookings", headers=auth_headers("admin"), params=params)
    assert_error(resp, 400, "VALIDATION_ERROR")


def test_admin_cancel_any_booking(client: TestClient):
    headers = auth_headers("admin")
    resp = client.delete("/api/admin/bookings/2", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"id": 2, "status": "cancelled"}

    resp_again = client.delete("/api/admin/bookings/2", headers=headers)
    assert_error(resp_again, 409, "ALREADY_CANCELLED")

    resp_missing = client.delete("/api/admin/bookings/999", headers=headers)
    assert_error(resp_missing, 404, "BOOKING_NOT_FOUND")


def test_admin_create_room_success(client: TestClient):
    resp = client.post(
        "/api/admin/rooms",
        headers=auth_headers("admin"),
        json={
            "name": "D-201",
            "building": "D",
            "floor": 2,
            "capacity": 25,
            "equipment": ["projector", "projector"],
        },
    )
    assert resp.status_code == 201
    room = resp.json()
    assert room["name"] == "D-201"
    assert room["building"] == "D"
    assert room["floor"] == 2
    assert room["capacity"] == 25
    assert room["equipment"] == ["projector"]

    rooms = client.get("/api/rooms").json()
    assert any(r["id"] == room["id"] and r["name"] == "D-201" for r in rooms)


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "building": "D", "floor": 2, "capacity": 25, "equipment": ["projector"]},
        {"name": "   ", "building": "D", "floor": 2, "capacity": 25, "equipment": []},
        {"name": "A-101", "building": "D", "floor": 2, "capacity": 25, "equipment": []},
        {"name": "D-201", "building": "Z", "floor": 2, "capacity": 25, "equipment": []},
        {"name": "D-201", "building": "D", "floor": 0, "capacity": 25, "equipment": []},
        {"name": "D-201", "building": "D", "floor": True, "capacity": 25, "equipment": []},
        {"name": "D-201", "building": "D", "floor": 2, "capacity": 0, "equipment": []},
        {"name": "D-201", "building": "D", "floor": 2, "capacity": -5, "equipment": []},
        {"name": "D-201", "building": "D", "floor": 2, "capacity": 25, "equipment": ["laser"]},
        {"name": "D-201", "building": "D", "floor": 2, "capacity": 25, "equipment": "projector"},
        {"building": "D", "floor": 2, "capacity": 25, "equipment": ["projector"]},
        {"name": "D-201", "floor": 2, "capacity": 25, "equipment": ["projector"]},
        {"name": "D-201", "building": "D", "capacity": 25, "equipment": ["projector"]},
        {"name": "D-201", "building": "D", "floor": 2, "equipment": ["projector"]},
        {"name": "D-201", "building": "D", "floor": 2, "capacity": 25},
        "not-a-dict",
    ],
)
def test_admin_create_room_validation_errors(client: TestClient, payload):
    resp = client.post(
        "/api/admin/rooms",
        headers=auth_headers("admin"),
        json=payload,
    )
    assert_error(resp, 400, "VALIDATION_ERROR")


def test_admin_update_room_success_and_same_name_allowed(client: TestClient):
    headers = auth_headers("admin")
    resp_same_name = client.put(
        "/api/admin/rooms/1",
        headers=headers,
        json={
            "name": "A-101",
            "building": "A",
            "floor": 1,
            "capacity": 35,
            "equipment": ["projector", "whiteboard", "video"],
        },
    )
    assert resp_same_name.status_code == 200
    assert resp_same_name.json()["capacity"] == 35
    assert resp_same_name.json()["equipment"] == ["projector", "whiteboard", "video"]

    fetched = client.get("/api/rooms/1").json()
    assert fetched["capacity"] == 35


def test_admin_update_room_errors(client: TestClient):
    headers = auth_headers("admin")

    resp_missing = client.put(
        "/api/admin/rooms/1",
        headers=headers,
        json={"name": "A-101", "building": "A", "floor": 1, "capacity": 30},
    )
    assert_error(resp_missing, 400, "VALIDATION_ERROR")

    # Имя уже занято другой комнатой (A-102)
    resp_dup = client.put(
        "/api/admin/rooms/1",
        headers=headers,
        json={
            "name": "A-102",
            "building": "A",
            "floor": 1,
            "capacity": 30,
            "equipment": ["projector"],
        },
    )
    assert_error(resp_dup, 400, "VALIDATION_ERROR")

    resp_404 = client.put(
        "/api/admin/rooms/999",
        headers=headers,
        json={
            "name": "Z-999",
            "building": "A",
            "floor": 1,
            "capacity": 30,
            "equipment": ["projector"],
        },
    )
    assert_error(resp_404, 404, "ROOM_NOT_FOUND")
