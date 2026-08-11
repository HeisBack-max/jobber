from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Fresh SQLite database per test, schema created directly from the
    ORM metadata (equivalent to `alembic upgrade head` for test purposes)."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("JOBINTEL_DATABASE_URL", f"sqlite:///{db_path}")

    from jobintel.settings import get_settings
    get_settings.cache_clear()

    from jobintel.db import session as db_session
    db_session.reset_engine_for_tests()

    from jobintel.db.models import Base
    Base.metadata.create_all(db_session.get_engine())

    yield db_session

    db_session.reset_engine_for_tests()
    get_settings.cache_clear()
