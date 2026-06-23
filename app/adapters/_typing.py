from __future__ import annotations

from typing import Any
from uuid import UUID


def to_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def require_uuid(value: Any, field_name: str) -> UUID:
    result = to_uuid(value)
    if result is None:
        raise ValueError(f"{field_name} is required")
    return result


def normalize_result(result: Any) -> dict[str, Any] | None:
    if result is None:
        return None
    if isinstance(result, dict):
        return result
    if hasattr(result, "to_dict"):
        return result.to_dict()
    return result

