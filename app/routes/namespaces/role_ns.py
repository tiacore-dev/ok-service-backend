import json
import logging
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app.schemas.role_schemas import RoleFilterSchema
from app.routes.models.role_models import (
    role_all_response,
    role_filter_parser,
    role_model
)


logger = logging.getLogger('ok_service')

role_ns = Namespace(
    'roles',
    description='Role management operations'
)

role_ns.models[role_all_response.name] = role_all_response
role_ns.models[role_model.name] = role_model


@role_ns.route('/all')
class RoleAll(Resource):
    @jwt_required()
    @role_ns.expect(role_filter_parser)
    @role_ns.marshal_with(role_all_response)
    def get(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to fetch all roles.",
                    extra={"login": current_user})

        schema = RoleFilterSchema()
        try:
            args = schema.load(request.args)
            logger.debug(f"Validated filters: {args}", extra={
                         "login": current_user})
        except ValidationError as err:
            logger.error(f"Validation error: {err.messages}", extra={
                         "login": current_user})
            return {"error": err.messages}, 400

        offset = args.get('offset', 0)
        limit = args.get('limit', None)
        sort_by = args.get('sort_by')
        sort_order = args.get('sort_order', 'desc')
        filters = {
            'role_id': args.get('role_id'),
            'name': args.get('name'),
        }

        logger.debug(
            f"Fetching roles with filters: {filters}, offset={offset}, limit={limit}, sort_by={sort_by}, sort_order={sort_order}",
            extra={"login": current_user}
        )

        try:
            from app.database.managers.roles_managers import RolesManager
            db = RolesManager()
            roles = db.get_all_filtered(
                offset, limit, sort_by, sort_order, **filters)
            logger.info(f"Successfully fetched {len(roles)} roles", extra={
                        "login": current_user})
            return {"roles": roles, "msg": "Roles found successfully"}, 200
        except Exception as e:
            logger.error(f"Error fetching roles: {e}", extra={
                         "login": current_user})
            return {'msg': f"Error during getting roles: {e}"}, 500
