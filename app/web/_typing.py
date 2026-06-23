from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping
from uuid import UUID


def require_mapping(value: Mapping[str, Any] | None, message: str) -> Mapping[str, Any]:
    if value is None:
        raise ValueError(message)
    return value


def to_plain_dict(value: Mapping[str, Any] | None, message: str) -> dict[str, Any]:
    return dict(require_mapping(value, message))


def has_field(payload: Mapping[str, Any], key: str) -> bool:
    return key in payload


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


def get_optional_uuid(payload: Mapping[str, Any], key: str) -> UUID | None:
    return optional_uuid(payload.get(key))


def get_required_uuid(payload: Mapping[str, Any], key: str, message: str) -> UUID:
    return required_uuid(payload.get(key), message)


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


def get_optional_decimal(payload: Mapping[str, Any], key: str) -> Decimal | None:
    value = payload.get(key)
    if value is None:
        return None
    return Decimal(str(value))


def get_optional_bool(payload: Mapping[str, Any], key: str) -> bool | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"true", "1", "yes", "on"}
    return bool(value)


def get_required_str(payload: Mapping[str, Any], key: str, message: str) -> str:
    value = get_optional_str(payload, key)
    if value is None:
        raise ValueError(message)
    return value


def get_required_int(payload: Mapping[str, Any], key: str, message: str) -> int:
    value = get_optional_int(payload, key)
    if value is None:
        raise ValueError(message)
    return value


def get_required_decimal(
    payload: Mapping[str, Any], key: str, message: str
) -> Decimal:
    value = get_optional_decimal(payload, key)
    if value is None:
        raise ValueError(message)
    return value
