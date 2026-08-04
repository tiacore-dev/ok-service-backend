from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_epoch_milliseconds() -> int:
    return int(utc_now().timestamp() * 1000)


def utc_epoch_seconds() -> int:
    """Backward-compatible helper; persisted timestamps use milliseconds."""
    return int(utc_now().timestamp())
