from __future__ import annotations

from typing import Any, Mapping, TypeVar
from uuid import UUID

T = TypeVar("T")


def require_mapping(value: Mapping[str, Any] | None, message: str) -> Mapping[str, Any]:
    if value is None:
        raise ValueError(message)
    return value


def to_plain_dict(value: Mapping[str, Any] | None, message: str) -> dict[str, Any]:
    return dict(require_mapping(value, message))


def optional_uuid(value: Any) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def required_uuid(value: Any, message: str) -> UUID:
    result = optional_uuid(value)
    if result is None:
        raise ValueError(message)
    return result


def get_optional_str(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    return str(value)


def get_optional_int(payload: Mapping[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    return int(value)


def get_optional_bool(payload: Mapping[str, Any], key: str) -> bool | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes", "on"}
    return bool(value)
