import json
import os
import subprocess
import sys
from datetime import datetime

from fastapi.testclient import TestClient

from app import clock
from app.db import get_connection
from app.main import create_app
from app.seed import reset_seed, seed_if_empty
from tests.conftest import DAY_AFTER, TODAY, TOMORROW, assert_error, auth_headers


def test_health_endpoint(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_seed_relative_dates(client: TestClient):
    resp = client.get("/api/admin/bookings", headers=auth_headers("admin"))
    assert resp.status_code == 200
    bookings = {b["id"]: b for b in resp.json()}
    assert set(bookings.keys()) == {1, 2, 3, 4, 5, 6, 7}

    for bid in (1, 2, 3, 4, 7):
        assert bookings[bid]["date"] == TOMORROW
    assert bookings[5]["date"] == TODAY
    assert bookings[5]["status"] == "cancelled"
    assert bookings[6]["date"] == DAY_AFTER


def test_seed_not_duplicated_on_restart(frozen_today, db_path):
    app1 = create_app()
    with TestClient(app1) as c1:
        assert len(c1.get("/api/rooms").json()) == 12
        r = c1.post(
            "/api/admin/rooms",
            headers=auth_headers("admin"),
            json={
                "name": "D-999",
                "building": "D",
                "floor": 9,
                "capacity": 10,
                "equipment": ["whiteboard"],
            },
        )
        assert r.status_code == 201

    # Повторный старт не должен дублировать или перетирать непустую БД
    assert seed_if_empty() is False
    app2 = create_app()
    with TestClient(app2) as c2:
        rooms = c2.get("/api/rooms").json()
        assert len(rooms) == 13


def test_seed_reset_restores_initial_state(frozen_today, db_path):
    app = create_app()
    with TestClient(app) as c:
        c.post(
            "/api/admin/rooms",
            headers=auth_headers("admin"),
            json={
                "name": "D-999",
                "building": "D",
                "floor": 9,
                "capacity": 10,
                "equipment": ["whiteboard"],
            },
        )
        assert len(c.get("/api/rooms").json()) == 13

    with clock.frozen_clock(datetime(2025, 11, 20, 9, 0, 0)):
        reset_seed()

    with get_connection() as conn:
        rooms_cnt = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
        b1_date = conn.execute("SELECT date FROM bookings WHERE id = 1").fetchone()[0]
    assert rooms_cnt == 12
    assert b1_date == "2025-11-21"


def test_seed_cli_reset(tmp_path):
    db_file = tmp_path / "cli_seed.db"
    env = {**os.environ, "CAMPUSFLOW_DB": str(db_file)}
    res = subprocess.run(
        [sys.executable, "-m", "app.seed", "--reset"],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    assert "reset and seeded" in res.stdout.lower()


def test_unknown_route_returns_unified_404(client: TestClient):
    resp = client.get("/api/nonexistent/route")
    assert_error(resp, 404, "NOT_FOUND")


def test_unexpected_exception_returns_unified_500(frozen_today, db_path):
    app = create_app()

    @app.get("/api/boom")
    def boom():
        raise RuntimeError("secret internal stack trace")

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/api/boom")
        body = assert_error(resp, 500, "INTERNAL_ERROR")
        assert "secret internal stack trace" not in resp.text
        assert body["details"] == {}


def test_utf8_charset_and_cyrillic_preservation(client: TestClient):
    resp = client.get("/api/bookings/my", headers=auth_headers("student1"))
    assert resp.status_code == 200
    assert resp.headers["content-type"].lower() == "application/json; charset=utf-8"
    raw_text = resp.content.decode("utf-8")
    assert "Консультация" in raw_text
    assert "\\u" not in raw_text
    data = json.loads(raw_text)
    assert data[0]["userDisplayName"] == "Иван Студентов"
