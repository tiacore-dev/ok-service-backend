from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_epoch_seconds() -> int:
    return int(utc_now().timestamp())


def utc_epoch_milliseconds() -> int:
    return int(utc_now().timestamp() * 1000)
