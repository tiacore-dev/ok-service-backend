import logging
import json
from functools import wraps
from flask import request
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException
from flask_jwt_extended import get_jwt_identity


logger = logging.getLogger('ok_service')


def log_exceptions_and_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        current_user = None
        try:
            current_user = json.loads(get_jwt_identity())
        except Exception:
            current_user = {
                "user_id": "anonymous",
                "login": request.remote_addr,
                "role": "unknown"
            }

        try:
            return func(*args, **kwargs)
        except ValidationError as err:
            logger.warning("Validation error", extra={"login": current_user})
            return {"error": err.messages}, 400
        except HTTPException as e:
            logger.warning(f"HTTPException {e.code}: {e.description}",
                           extra={"login": current_user})
            return {"msg": e.description}, e.code
        except Exception as e:
            logger.error(f"Unexpected error: {e}",
                         extra={"login": current_user})
            return {"msg": "Internal server error"}, 500
    return wrapper
