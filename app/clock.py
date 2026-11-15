from contextlib import contextmanager
from datetime import date, datetime
from typing import Iterator

_override_now: datetime | None = None


def now() -> datetime:
    """Текущее время (или подменённое в тестах)."""
    if _override_now is not None:
        return _override_now
    return datetime.now()


def today() -> date:
    """Текущая дата по часам приложения."""
    return now().date()


def set_now(dt: datetime | None) -> None:
    """Зафиксировать текущее время для тестов; None сбрасывает обратно на системное."""
    global _override_now
    _override_now = dt


def reset_clock() -> None:
    set_now(None)


@contextmanager
def frozen_clock(dt: datetime) -> Iterator[datetime]:
    """Временно заморозить clock.now() на время блока with."""
    prev = _override_now
    set_now(dt)
    try:
        yield dt
    finally:
        set_now(prev)
