from functools import wraps

from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError

from app.decorators import api_key_or_jwt_required


def template_auth_required(func):
    """Use the shared permission gate while preserving template JWT errors."""
    authenticated = api_key_or_jwt_required(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return authenticated(*args, **kwargs)
        except (JWTExtendedException, PyJWTError):
            return {"msg": "Unauthorized"}, 401

    return wrapper
