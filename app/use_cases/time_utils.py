from __future__ import annotations

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_epoch_seconds() -> int:
    return int(utc_now().timestamp())
