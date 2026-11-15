import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "campusflow.db"


def get_db_path() -> Path:
    """Путь к файлу SQLite: из CAMPUSFLOW_DB или campusflow.db в корне проекта."""
    raw = os.environ.get("CAMPUSFLOW_DB")
    if raw:
        return Path(raw)
    return DEFAULT_DB_PATH
