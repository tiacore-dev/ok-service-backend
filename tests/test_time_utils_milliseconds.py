from datetime import UTC, datetime

from app.database import time_utils as database_time_utils
from app.use_cases import time_utils as use_case_time_utils


def test_database_epoch_milliseconds(monkeypatch):
    monkeypatch.setattr(
        database_time_utils,
        "utc_now",
        lambda: datetime(2026, 8, 4, 12, 34, 56, 789000, tzinfo=UTC),
    )

    assert database_time_utils.utc_epoch_milliseconds() == 1785846896789


def test_use_case_epoch_milliseconds(monkeypatch):
    monkeypatch.setattr(
        use_case_time_utils,
        "utc_now",
        lambda: datetime(2026, 8, 4, 12, 34, 56, 789000, tzinfo=UTC),
    )

    assert use_case_time_utils.utc_epoch_milliseconds() == 1785846896789
