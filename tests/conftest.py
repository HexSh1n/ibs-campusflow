from datetime import datetime
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from app import clock
from app.main import create_app

FROZEN_NOW = datetime(2025, 11, 12, 8, 0, 0)
YESTERDAY = "2025-11-11"
TODAY = "2025-11-12"
TOMORROW = "2025-11-13"
DAY_AFTER = "2025-11-14"


@pytest.fixture()
def frozen_today() -> Iterator[datetime]:
    """Фиксирует clock.now() на 2025-11-12 08:00, чтобы даты сидов не зависели от календаря."""
    clock.set_now(FROZEN_NOW)
    try:
        yield FROZEN_NOW
    finally:
        clock.reset_clock()


@pytest.fixture()
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Подставляет отдельный временный файл SQLite для каждого теста."""
    target = tmp_path / "test_campusflow.db"
    monkeypatch.setenv("CAMPUSFLOW_DB", str(target))
    return target


@pytest.fixture()
def client(frozen_today: datetime, db_path: Path) -> Iterator[TestClient]:
    """Тестовый клиент со свежезасеянной БД."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(login: str) -> dict[str, str]:
    return {"Authorization": f"Bearer mock-token-{login}"}


def assert_error(response, expected_status: int, expected_code: str) -> dict:
    """Проверяет HTTP-код и единый формат ответа об ошибке {code, message, details}."""
    assert response.status_code == expected_status, (
        f"Ожидали {expected_status}, получили {response.status_code}: {response.text}"
    )
    body = response.json()
    assert isinstance(body, dict)
    assert body.get("code") == expected_code
    assert isinstance(body.get("message"), str) and body["message"]
    assert isinstance(body.get("details"), dict)
    return body
