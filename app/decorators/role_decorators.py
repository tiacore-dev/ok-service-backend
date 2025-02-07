import logging
import json
from functools import wraps
from flask_jwt_extended import get_jwt_identity


logger = logging.getLogger("ok_service")


def admin_required(func):
    """Декоратор для проверки, что текущий пользователь — администратор."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        current_user = json.loads(get_jwt_identity())
        if current_user.get("role") != "admin":
            logger.warning("Несанкционированный доступ: требуется администратор.",
                           extra={"login": current_user.get("login")})
            return {"msg": "Forbidden"}, 403
        return func(*args, **kwargs)
    return wrapper


def user_forbidden(func):
    """Декоратор для проверки, что текущий пользователь — администратор."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        current_user = json.loads(get_jwt_identity())
        if current_user.get("role") == "user":
            logger.warning("Несанкционированный доступ: недостаточно прав.",
                           extra={"login": current_user.get("login")})
            return {"msg": "Forbidden"}, 403
        return func(*args, **kwargs)
    return wrapper
