import json
import logging
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.routes.models.object_status_models import (
    object_status_all_response,
    object_status_filter_parser,
    object_status_model
)

logger = logging.getLogger('ok_service')

object_status_ns = Namespace(
    'object_statuses',
    description='Object Status management operations'
)

object_status_ns.models[object_status_all_response.name] = object_status_all_response
object_status_ns.models[object_status_model.name] = object_status_model


@object_status_ns.route('/all')
class ObjectStatusAll(Resource):
    @jwt_required()
    @object_status_ns.expect(object_status_filter_parser)
    @object_status_ns.marshal_with(object_status_all_response)
    @object_status_ns.response(500, "Internal Server Error")
    def get(self):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            "Request to fetch all object statuses.",
            extra={"login": current_user.get('login')}
        )

        args = object_status_filter_parser.parse_args()
        offset = args.get('offset', 0)
        limit = args.get('limit', None)
        sort_by = args.get('sort_by')
        sort_order = args.get('sort_order', 'asc')
        filters = {
            'object_status_id': args.get('object_status_id'),
            'name': args.get('name')
        }

        logger.debug(
            f"Filter parameters: offset={offset}, limit={limit}, sort_by={
                sort_by}, sort_order={sort_order}, filters={filters}",
            extra={"login": current_user.get('login')}
        )

        try:
            from app.database.managers.objects_managers import ObjectStatusesManager
            db = ObjectStatusesManager()
            logger.debug("Fetching object statuses from the database...", extra={
                         "login": current_user.get('login')})
            object_statuses = db.get_all_filtered(
                offset, limit, sort_by, sort_order, **filters)
            logger.info(
                f"Successfully fetched object statuses: count={
                    len(object_statuses)}",
                extra={"login": current_user.get('login')}
            )
            return {"object_statuses": object_statuses, "msg": "Object statuses found successfully"}, 200
        except Exception as e:
            logger.error(
                f"Error fetching object statuses: {e}",
                extra={"login": current_user.get('login')}
            )
            return {'msg': f"Error during getting object statuses: {e}"}, 500
