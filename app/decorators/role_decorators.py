import json
import logging
from functools import wraps

from flask import g
from flask_jwt_extended import get_jwt_identity

logger = logging.getLogger("ok_service")


def _get_current_user() -> dict:
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return identity
    if isinstance(identity, (str, bytes, bytearray)):
        try:
            parsed = json.loads(identity)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def admin_required(func):
    """Декоратор для проверки, что текущий пользователь — администратор."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if getattr(g, "auth_via_api_key", False):
            return func(*args, **kwargs)
        current_user = _get_current_user()
        if current_user.get("role") != "admin":
            logger.warning(
                "Несанкционированный доступ: требуется администратор.",
                extra={"login": current_user},
            )
            return {"msg": "Forbidden"}, 403
        return func(*args, **kwargs)

    return wrapper


def admin_or_manager_required(func):
    """Allow mutation only to administrators and managers."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if getattr(g, "auth_via_api_key", False):
            return func(*args, **kwargs)
        current_user = _get_current_user()
        if current_user.get("role") not in {"admin", "manager"}:
            return {"msg": "Forbidden"}, 403
        return func(*args, **kwargs)

    return wrapper


def user_forbidden(func):
    """Декоратор для проверки, что текущий пользователь — администратор."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        current_user = _get_current_user()
        if current_user.get("role") == "user":
            logger.warning(
                "Несанкционированный доступ: недостаточно прав.",
                extra={"login": current_user},
            )
            return {"msg": "Forbidden"}, 403
        return func(*args, **kwargs)

    return wrapper
