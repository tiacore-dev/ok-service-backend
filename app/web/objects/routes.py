from __future__ import annotations

import json
import logging
from typing import Any, TypedDict, cast
from uuid import UUID

from flask import g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.objects import (
    SQLAlchemyObjectRepository,
    object_entity_to_response,
)
from app.adapters.attachments import list_attachment_view_data
from app.adapters.places import SQLAlchemyPlaceRepository, place_entity_to_response
from app.decorators import api_key_or_jwt_required
from app.domain.objects import (
    ObjectStatus,
    ObjectForbiddenError,
    ObjectNotFoundError,
    ObjectValidationError,
)
from app.schemas.object_schemas import (
    ObjectCreateSchema,
    ObjectEditSchema,
    ObjectFilterSchema,
)
from app.use_cases.objects import (
    CreateObjectCommand,
    CreateObjectUseCase,
    GetObjectUseCase,
    GetObjectStatsUseCase,
    GetAllObjectsStatsUseCase,
    GetObjectStatsDetailsUseCase,
    ObjectStatsListQuery,
    HardDeleteObjectUseCase,
    ListObjectsUseCase,
    ObjectActor,
    ObjectListQuery,
    SoftDeleteObjectUseCase,
    UpdateObjectCommand,
    UpdateObjectUseCase,
)
from app.use_cases.places import ListPlacesForObjectUseCase
from app.web.attachments.contract import attachment_view_model
from app.web._typing import (
    get_optional_bool,
    get_optional_float,
    get_optional_int,
    get_optional_str,
    get_optional_uuid,
    get_required_uuid,
    to_plain_dict,
)

from .models import (
    object_all_response,
    object_create_model,
    object_edit_model,
    object_filter_parser,
    object_model,
    object_msg_model,
    object_response,
    object_view_model,
    object_status_item_model,
    object_statuses_response,
    object_stats_response,
    object_stats_details_response,
    object_stats_collection_response,
    stats_collection_filter_parser,
)

logger = logging.getLogger("ok_service")

object_ns = Namespace("objects", description="Objects management operations")

object_ns.models[object_create_model.name] = object_create_model
object_ns.models[object_edit_model.name] = object_edit_model
object_ns.models[object_msg_model.name] = object_msg_model
object_ns.models[object_response.name] = object_response
object_ns.models[object_all_response.name] = object_all_response
object_ns.models[object_model.name] = object_model
object_ns.models[object_view_model.name] = object_view_model
object_ns.models[object_status_item_model.name] = object_status_item_model
object_ns.models[object_statuses_response.name] = object_statuses_response
object_ns.models[object_stats_response.name] = object_stats_response
object_ns.models[object_stats_details_response.name] = object_stats_details_response
object_ns.models[object_stats_collection_response.name] = object_stats_collection_response
object_ns.models[attachment_view_model.name] = attachment_view_model


@object_ns.route("/statuses")
class ObjectStatuses(Resource):
    @api_key_or_jwt_required
    @object_ns.marshal_with(object_statuses_response)
    def get(self):
        return {
            "msg": "Object statuses found successfully",
            "statuses": [
                {"value": status.value, "label": status.label}
                for status in ObjectStatus
            ],
        }, 200


@object_ns.route("/<string:object_id>/get-stat")
class ObjectStats(Resource):
    @api_key_or_jwt_required
    @object_ns.marshal_with(object_stats_response)
    def get(self, object_id):
        current_user = _get_current_user()
        try:
            stats = GetObjectStatsUseCase(repository=_repository()).execute(
                _parse_object_id(object_id), _actor(current_user)
            )
            return {"msg": "Object stats fetched successfully", "stats": stats}, 200
        except Exception as error:
            logger.error("Error getting object stats: %s", error)
            return _map_error(error)


@object_ns.route("/get-stat")
class AllObjectsStats(Resource):
    @api_key_or_jwt_required
    @object_ns.expect(stats_collection_filter_parser)
    @object_ns.marshal_with(object_stats_collection_response)
    def get(self):
        current_user = _get_current_user()
        try:
            data = stats_collection_filter_parser.parse_args()
            if data.offset < 0 or data.limit < 1:
                raise ValueError("offset must be non-negative and limit must be positive")
            stats = GetAllObjectsStatsUseCase(repository=_repository()).execute(
                ObjectStatsListQuery(
                    offset=data.offset, limit=data.limit, search=data.search
                ),
                _actor(current_user),
            )
            return {"msg": "Objects stats fetched successfully", "stats": stats}, 200
        except Exception as error:
            logger.error("Error getting all objects stats: %s", error)
            return _map_error(error)


@object_ns.route("/<string:object_id>/get-stat-details")
class ObjectStatsDetails(Resource):
    @api_key_or_jwt_required
    @object_ns.marshal_with(object_stats_details_response)
    def get(self, object_id):
        current_user = _get_current_user()
        try:
            stats = GetObjectStatsDetailsUseCase(repository=_repository()).execute(
                _parse_object_id(object_id), _actor(current_user)
            )
            return {
                "msg": "Object detailed stats fetched successfully",
                "stats": stats,
            }, 200
        except Exception as error:
            logger.error("Error getting detailed object stats: %s", error)
            return _map_error(error)


class ObjectCreatePayload(TypedDict):
    name: str
    address: str | None
    description: str | None
    manager: str | None
    status: str | None
    city: str
    lng: float | None
    ltd: float | None


class ObjectEditPayload(TypedDict, total=False):
    name: str | None
    address: str | None
    description: str | None
    status: str | None
    manager: str | None
    deleted: bool | None
    city: str | None
    lng: float | None
    ltd: float | None


class ObjectFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
    address: str
    status: str
    name: str
    manager: str
    deleted: bool
    city: str
    lng: float
    ltd: float
    created_by: str
    created_at: int


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


def _repository() -> SQLAlchemyObjectRepository:
    return SQLAlchemyObjectRepository()


def _places_repository() -> SQLAlchemyPlaceRepository:
    return SQLAlchemyPlaceRepository()


def _parse_object_id(object_id: str) -> UUID:
    return get_required_uuid(
        {"object_id": object_id}, "object_id", "Invalid UUID format"
    )


def _actor(current_user: dict[str, Any]) -> ObjectActor:
    return ObjectActor(
        role=str(current_user.get("role", "")),
        user_id=get_required_uuid(
            current_user, "user_id", "Current user id is required"
        ),
    )


def _map_error(error: Exception):
    if isinstance(error, ObjectNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, ObjectForbiddenError):
        return {"msg": str(error)}, 403
    if isinstance(error, ObjectValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete object: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@object_ns.route("/add")
class ObjectAdd(Resource):
    @api_key_or_jwt_required
    @object_ns.expect(object_create_model)
    @object_ns.marshal_with(object_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info("Request to add new object", extra={"login": current_user})
        if current_user.get("role") != "admin":
            return {"msg": "Forbidden"}, 403
        schema = ObjectCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(ObjectCreatePayload, schema.load(raw_payload))
            obj = CreateObjectUseCase(repository=_repository()).execute(
                CreateObjectCommand(
                    name=data["name"],
                    address=data.get("address"),
                    description=data.get("description"),
                    manager=get_optional_uuid(data, "manager"),
                    status=data.get("status"),
                    city=get_required_uuid(data, "city", "City is required"),
                    lng=get_optional_float(data, "lng"),
                    ltd=get_optional_float(data, "ltd"),
                    created_by=get_required_uuid(
                        current_user, "user_id", "Current user id is required"
                    ),
                ),
                _actor(current_user),
            )
            return {
                "msg": "New object added successfully",
                "object_id": str(obj.object_id),
            }, 200
        except Exception as error:
            logger.error(f"Error adding object: {error}", extra={"login": current_user})
            return _map_error(error)


@object_ns.route("/<string:object_id>/view")
class ObjectView(Resource):
    @api_key_or_jwt_required
    @object_ns.marshal_with(object_response)
    def get(self, object_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to view object: {object_id}", extra={"login": current_user}
        )
        try:
            obj = GetObjectUseCase(repository=_repository()).execute(
                _parse_object_id(object_id),
                _actor(current_user),
            )
            places = ListPlacesForObjectUseCase(
                repository=_places_repository()
            ).execute(obj.object_id)
            object_response_data = object_entity_to_response(obj)
            object_response_data["places"] = [
                place_entity_to_response(place) for place in places
            ]
            object_response_data["attachments"] = list_attachment_view_data(
                "object", obj.object_id
            )
            return {
                "msg": "Object found successfully",
                "object": object_response_data,
            }, 200
        except Exception as error:
            logger.error(
                f"Error viewing object: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@object_ns.route("/<string:object_id>/delete/soft")
class ObjectSoftDelete(Resource):
    @api_key_or_jwt_required
    @object_ns.marshal_with(object_msg_model)
    def patch(self, object_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to soft delete object: {object_id}", extra={"login": current_user}
        )
        if current_user.get("role") != "admin":
            return {"msg": "Forbidden"}, 403
        try:
            SoftDeleteObjectUseCase(repository=_repository()).execute(
                _parse_object_id(object_id),
                _actor(current_user),
            )
            return {
                "msg": f"Object {object_id} soft deleted successfully",
                "object_id": object_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error soft deleting object: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@object_ns.route("/<string:object_id>/delete/hard")
class ObjectHardDelete(Resource):
    @api_key_or_jwt_required
    @object_ns.marshal_with(object_msg_model)
    def delete(self, object_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete object: {object_id}", extra={"login": current_user}
        )
        if current_user.get("role") != "admin":
            return {"msg": "Forbidden"}, 403
        try:
            HardDeleteObjectUseCase(repository=_repository()).execute(
                _parse_object_id(object_id),
                _actor(current_user),
            )
            return {
                "msg": f"Object {object_id} hard deleted successfully",
                "object_id": object_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error hard deleting object: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@object_ns.route("/<string:object_id>/edit")
class ObjectEdit(Resource):
    @api_key_or_jwt_required
    @object_ns.expect(object_edit_model)
    @object_ns.marshal_with(object_msg_model)
    def patch(self, object_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to edit object: {object_id}", extra={"login": current_user}
        )
        if current_user.get("role") != "admin":
            return {"msg": "Forbidden"}, 403
        schema = ObjectEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(ObjectEditPayload, schema.load(raw_payload))
            if not any(value is not None for value in data.values()):
                raise ValueError("No data provided for update")
            obj = UpdateObjectUseCase(repository=_repository()).execute(
                UpdateObjectCommand(
                    object_id=_parse_object_id(object_id),
                    name=data.get("name"),
                    address=data.get("address"),
                    description=data.get("description"),
                    status=data.get("status"),
                    manager=get_optional_uuid(data, "manager"),
                    deleted=get_optional_bool(data, "deleted"),
                    city=get_optional_uuid(data, "city"),
                    lng=get_optional_float(data, "lng"),
                    ltd=get_optional_float(data, "ltd"),
                ),
                _actor(current_user),
            )
            return {
                "msg": "Object edited successfully",
                "object_id": str(obj.object_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error editing object: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@object_ns.route("/all")
class ObjectAll(Resource):
    @api_key_or_jwt_required
    @object_ns.expect(object_filter_parser)
    @object_ns.marshal_with(object_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all objects", extra={"login": current_user})
        schema = ObjectFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            data = cast(ObjectFilterPayload, schema.load(raw_args))
            actor = _actor(current_user)
            query = ObjectListQuery(
                offset=data.get("offset", 0),
                limit=data.get("limit", 10),
                sort_by=data.get("sort_by"),
                sort_order=data.get("sort_order", "desc"),
                address=get_optional_str(data, "address"),
                status=get_optional_str(data, "status"),
                name=get_optional_str(data, "name"),
                manager=get_optional_uuid(data, "manager"),
                deleted=get_optional_bool(data, "deleted"),
                city=get_optional_uuid(data, "city"),
                lng=get_optional_float(data, "lng"),
                ltd=get_optional_float(data, "ltd"),
                created_by=get_optional_uuid(data, "created_by"),
                created_at=get_optional_int(data, "created_at"),
            )
            if actor.role == "user":
                query = ObjectListQuery(
                    offset=query.offset,
                    limit=query.limit,
                    sort_by=query.sort_by,
                    sort_order=query.sort_order,
                    address=query.address,
                    status="active",
                    name=query.name,
                    manager=query.manager,
                    deleted=query.deleted,
                    city=query.city,
                    lng=query.lng,
                    ltd=query.ltd,
                    created_by=query.created_by,
                    created_at=query.created_at,
                )
            objects = ListObjectsUseCase(repository=_repository()).execute(query, actor)
            return {
                "msg": "Objects found successfully",
                "objects": [object_entity_to_response(obj) for obj in objects],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching objects: {error}", extra={"login": current_user}
            )
            return _map_error(error)
