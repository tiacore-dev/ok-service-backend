from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_epoch_milliseconds() -> int:
    return int(utc_now().timestamp() * 1000)


def utc_epoch_seconds() -> int:
    """Backward-compatible helper for non-persistent duration code."""
    return int(utc_now().timestamp())
