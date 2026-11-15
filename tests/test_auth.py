import pytest
from fastapi.testclient import TestClient

from tests.conftest import assert_error


def test_login_student1_success(client: TestClient):
    resp = client.post(
        "/api/auth/login",
        json={"login": "student1", "password": "student1"},
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "token": "mock-token-student1",
        "user": {
            "id": 1,
            "login": "student1",
            "displayName": "Иван Студентов",
            "role": "student",
        },
    }


def test_login_admin_success(client: TestClient):
    resp = client.post(
        "/api/auth/login",
        json={"login": "admin", "password": "admin"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token"] == "mock-token-admin"
    assert body["user"]["role"] == "admin"
    assert body["user"]["id"] == 3


def test_login_wrong_password(client: TestClient):
    resp = client.post(
        "/api/auth/login",
        json={"login": "student1", "password": "wrong"},
    )
    assert_error(resp, 401, "UNAUTHORIZED")


def test_login_unknown_user(client: TestClient):
    resp = client.post(
        "/api/auth/login",
        json={"login": "ghost", "password": "ghost"},
    )
    assert_error(resp, 401, "UNAUTHORIZED")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"login": "student1"},
        {"password": "student1"},
        {"login": "", "password": "student1"},
        {"login": 123, "password": "123"},
        ["not", "a", "dict"],
    ],
)
def test_login_validation_errors(client: TestClient, payload):
    resp = client.post("/api/auth/login", json=payload)
    assert_error(resp, 400, "VALIDATION_ERROR")


def test_login_empty_and_invalid_json_body(client: TestClient):
    resp_empty = client.post(
        "/api/auth/login",
        content=b"",
        headers={"Content-Type": "application/json"},
    )
    assert_error(resp_empty, 400, "VALIDATION_ERROR")

    resp_bad = client.post(
        "/api/auth/login",
        content=b"{bad json",
        headers={"Content-Type": "application/json"},
    )
    assert_error(resp_bad, 400, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic dXNlcjpwYXNz"},
        {"Authorization": "Bearer"},
        {"Authorization": "Bearer   "},
        {"Authorization": "Bearer wrong-prefix-student1"},
        {"Authorization": "Bearer mock-token-"},
        {"Authorization": "Bearer mock-token-unknown"},
    ],
)
def test_protected_endpoint_rejects_missing_or_invalid_auth(client: TestClient, headers):
    resp_my = client.get("/api/bookings/my", headers=headers)
    assert_error(resp_my, 401, "UNAUTHORIZED")

    # Даже при пустом теле авторизация должна проверяться до валидации тела
    resp_post = client.post("/api/bookings", headers=headers, json={})
    assert_error(resp_post, 401, "UNAUTHORIZED")
