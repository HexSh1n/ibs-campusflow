from fastapi.testclient import TestClient

from tests.conftest import assert_error, auth_headers


def test_my_bookings_all_for_student1(client: TestClient):
    resp = client.get("/api/bookings/my", headers=auth_headers("student1"))
    assert resp.status_code == 200
    assert [b["id"] for b in resp.json()] == [1, 5, 7]


def test_my_bookings_filter_by_status(client: TestClient):
    active = client.get(
        "/api/bookings/my",
        headers=auth_headers("student1"),
        params={"status": "active"},
    )
    assert active.status_code == 200
    assert [b["id"] for b in active.json()] == [1, 7]

    cancelled = client.get(
        "/api/bookings/my",
        headers=auth_headers("student1"),
        params={"status": "cancelled"},
    )
    assert cancelled.status_code == 200
    assert [b["id"] for b in cancelled.json()] == [5]


def test_my_bookings_invalid_status(client: TestClient):
    resp = client.get(
        "/api/bookings/my",
        headers=auth_headers("student1"),
        params={"status": "foo"},
    )
    assert_error(resp, 400, "VALIDATION_ERROR")


def test_my_bookings_requires_auth(client: TestClient):
    resp = client.get("/api/bookings/my")
    assert_error(resp, 401, "UNAUTHORIZED")


def test_cancel_own_booking_success(client: TestClient):
    resp = client.delete("/api/bookings/1", headers=auth_headers("student1"))
    assert resp.status_code == 200
    assert resp.json() == {"id": 1, "status": "cancelled"}

    active_after = client.get(
        "/api/bookings/my",
        headers=auth_headers("student1"),
        params={"status": "active"},
    )
    assert [b["id"] for b in active_after.json()] == [7]


def test_cancel_foreign_booking_forbidden_for_student_and_admin(client: TestClient):
    # Бронь 2 принадлежит student2
    resp_student = client.delete("/api/bookings/2", headers=auth_headers("student1"))
    assert_error(resp_student, 403, "FORBIDDEN")

    # Админ отменяет чужие брони через /api/admin/bookings/{id}, а здесь получает 403
    resp_admin = client.delete("/api/bookings/2", headers=auth_headers("admin"))
    assert_error(resp_admin, 403, "FORBIDDEN")


def test_cancel_booking_not_found(client: TestClient):
    resp = client.delete("/api/bookings/999", headers=auth_headers("student1"))
    assert_error(resp, 404, "BOOKING_NOT_FOUND")


def test_cancel_booking_already_cancelled(client: TestClient):
    # Бронь 5 уже отменена в seed
    resp_seed = client.delete("/api/bookings/5", headers=auth_headers("student1"))
    assert_error(resp_seed, 409, "ALREADY_CANCELLED")

    first = client.delete("/api/bookings/1", headers=auth_headers("student1"))
    assert first.status_code == 200
    second = client.delete("/api/bookings/1", headers=auth_headers("student1"))
    assert_error(second, 409, "ALREADY_CANCELLED")
