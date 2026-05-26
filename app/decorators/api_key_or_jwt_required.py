import json
import logging
import re
from functools import wraps

from flask import g, request
from flask_jwt_extended import verify_jwt_in_request

from app.database.db_globals import Session
from app.database.models import (
    ApiKeys,
    KeyPermissionTypeRelations,
    PermissionTypes,
    Users,
)

logger = logging.getLogger("ok_service")


def _normalize_rule(rule: str) -> str:
    return re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", rule)


def _resolve_permission_description() -> str | None:
    if not request.url_rule:
        return None
    normalized_rule = _normalize_rule(request.url_rule.rule)
    return f"{request.method} {normalized_rule}"


def api_key_or_jwt_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        raw_api_key = request.headers.get("API-Key")
        g.auth_via_api_key = False

        if not raw_api_key:
            verify_jwt_in_request()
            return func(*args, **kwargs)

        permission_description = _resolve_permission_description()
        if not permission_description:
            return {"msg": "Forbidden"}, 403

        session = Session()
        try:
            api_key = session.query(ApiKeys).filter_by(token=raw_api_key).first()
            if not api_key:
                return {"msg": "Invalid API key"}, 403

            if api_key.expires_at is not None:
                import time

                if int(time.time()) > int(api_key.expires_at):
                    return {"msg": "API key expired"}, 403

            permission = (
                session.query(PermissionTypes)
                .filter_by(description=permission_description)
                .first()
            )
            if not permission:
                return {"msg": "Forbidden"}, 403

            has_permission = (
                session.query(KeyPermissionTypeRelations)
                .filter_by(
                    api_key_id=api_key.api_key_id,
                    permission_type_id=permission.permission_type_id,
                )
                .first()
            )
            if not has_permission:
                return {"msg": "Forbidden"}, 403

            admin_user = (
                session.query(Users).filter_by(role="admin", deleted=False).first()
            )
            g.auth_via_api_key = True
            g.api_key_id = str(api_key.api_key_id)
            g.api_key_identity_json = json.dumps(
                {
                    "role": "admin",
                    "login": "api_key",
                    "user_id": str(admin_user.user_id) if admin_user else None,
                }
            )
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API key auth error: {e}", extra={"login": "system"})
            return {"msg": "Forbidden"}, 403
        finally:
            session.close()

    return wrapper
