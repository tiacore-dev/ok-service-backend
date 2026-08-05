import json
import logging

from flask import g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError

from app.decorators import api_key_or_jwt_required
from app.schemas.role_schemas import RoleFilterSchema

from .models import role_all_response, role_filter_parser, role_model

logger = logging.getLogger("ok_service")

role_ns = Namespace("roles", description="Role management operations")

role_ns.models[role_all_response.name] = role_all_response
role_ns.models[role_model.name] = role_model


def _get_current_user():
    identity = (
        getattr(g, "api_key_identity_json", None)
        if getattr(g, "auth_via_api_key", False)
        else _get_jwt_identity()
    )
    if isinstance(identity, dict):
        return identity
    if isinstance(identity, (str, bytes, bytearray)):
        try:
            parsed = json.loads(identity)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


@role_ns.route("/all")
class RoleAll(Resource):
    @api_key_or_jwt_required
    @role_ns.expect(role_filter_parser)
    @role_ns.marshal_with(role_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all roles.", extra={"login": current_user})

        schema = RoleFilterSchema()
        try:
            args = schema.load(request.args)
            logger.debug(f"Validated filters: {args}", extra={"login": current_user})
        except ValidationError as err:
            logger.error(
                f"Validation error: {err.messages}", extra={"login": current_user}
            )
            return {"error": err.messages}, 400

        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit", None)  # type: ignore
        sort_by = args.get("sort_by")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore
        filters = {
            "role_id": args.get("role_id"),  # type: ignore
            "name": args.get("name"),  # type: ignore
        }

        logger.debug(
            f"Fetching roles with filters: {filters}, offset={offset}, limit={
                limit
            }, sort_by={sort_by}, sort_order={sort_order}",
            extra={"login": current_user},
        )

        try:
            from app.database.managers.roles_managers import RolesManager

            db = RolesManager()
            roles = db.get_all_filtered(offset, limit, sort_by, sort_order, **filters)  # type: ignore
            logger.info(
                f"Successfully fetched {len(roles)} roles",
                extra={"login": current_user},
            )
            return {"roles": roles, "msg": "Roles found successfully"}, 200
        except Exception as e:
            logger.error(f"Error fetching roles: {e}", extra={"login": current_user})
            return {"msg": f"Error during getting roles: {e}"}, 500
