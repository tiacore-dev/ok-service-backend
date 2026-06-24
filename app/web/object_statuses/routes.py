from __future__ import annotations

import json
import logging
from typing import Any, TypedDict, cast

from flask import g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError

from app.adapters.object_statuses import (
    SQLAlchemyObjectStatusRepository,
    object_status_entity_to_response,
)
from app.decorators import api_key_or_jwt_required
from app.schemas.object_status_schemas import ObjectStatusFilterSchema
from app.use_cases.object_statuses import (
    ListObjectStatusesUseCase,
    ObjectStatusListQuery,
)
from app.web._typing import get_optional_str, to_plain_dict

from .models import (
    object_status_all_response,
    object_status_filter_parser,
    object_status_model,
)

logger = logging.getLogger("ok_service")

object_status_ns = Namespace(
    "object_statuses", description="Object Status management operations"
)

object_status_ns.models[object_status_all_response.name] = object_status_all_response
object_status_ns.models[object_status_model.name] = object_status_model


class ObjectStatusFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
    object_status_id: str
    name: str


def get_jwt_identity():
    if getattr(g, "auth_via_api_key", False):
        return getattr(g, "api_key_identity_json", None)
    return _get_jwt_identity()


def _get_current_user() -> dict[str, Any]:
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


def _repository() -> SQLAlchemyObjectStatusRepository:
    return SQLAlchemyObjectStatusRepository()


@object_status_ns.route("/all")
class ObjectStatusAll(Resource):
    @api_key_or_jwt_required
    @object_status_ns.expect(object_status_filter_parser)
    @object_status_ns.marshal_with(object_status_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info(
            "Request to fetch all object statuses.", extra={"login": current_user}
        )
        schema = ObjectStatusFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            data = cast(ObjectStatusFilterPayload, schema.load(raw_args))
            statuses = ListObjectStatusesUseCase(repository=_repository()).execute(
                ObjectStatusListQuery(
                    offset=data.get("offset", 0),
                    limit=data.get("limit", 10),
                    sort_by=data.get("sort_by"),
                    sort_order=data.get("sort_order", "desc"),
                    object_status_id=get_optional_str(data, "object_status_id"),
                    name=get_optional_str(data, "name"),
                )
            )
            return {
                "object_statuses": [
                    object_status_entity_to_response(status) for status in statuses
                ],
                "msg": "Object statuses found successfully",
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching object statuses: {error}",
                extra={"login": current_user},
            )
            if isinstance(error, ValidationError):
                return {"error": error.messages}, 400
            if isinstance(error, ValueError):
                return {"msg": str(error)}, 400
            return {"msg": f"Error during getting object statuses: {error}"}, 500
