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

from app.adapters.positions import (
    SQLAlchemyPositionRepository,
    position_entity_to_response,
)
from app.decorators import admin_required, api_key_or_jwt_required
from app.domain.positions import PositionNotFoundError, PositionValidationError
from app.schemas.position_schemas import (
    PositionCreateSchema,
    PositionEditSchema,
    PositionFilterSchema,
)
from app.use_cases.positions import (
    CreatePositionCommand,
    CreatePositionUseCase,
    DeletePositionUseCase,
    GetPositionUseCase,
    ListPositionsUseCase,
    PositionListQuery,
    UpdatePositionCommand,
    UpdatePositionUseCase,
)
from app.web._typing import get_optional_str, get_required_uuid, to_plain_dict

from .models import (
    position_all_response,
    position_create_model,
    position_edit_model,
    position_filter_parser,
    position_model,
    position_msg_model,
    position_response,
)

logger = logging.getLogger("ok_service")

position_ns = Namespace("positions", description="Position management operations")

position_ns.models[position_create_model.name] = position_create_model
position_ns.models[position_edit_model.name] = position_edit_model
position_ns.models[position_msg_model.name] = position_msg_model
position_ns.models[position_response.name] = position_response
position_ns.models[position_all_response.name] = position_all_response
position_ns.models[position_model.name] = position_model


class PositionCreatePayload(TypedDict):
    name: str


class PositionEditPayload(TypedDict, total=False):
    name: str


class PositionFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
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


def _repository() -> SQLAlchemyPositionRepository:
    return SQLAlchemyPositionRepository()


def _parse_position_id(position_id: str) -> UUID:
    return get_required_uuid(
        {"position_id": position_id}, "position_id", "Invalid UUID format"
    )


def _map_error(error: Exception):
    if isinstance(error, PositionNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, PositionValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete position: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@position_ns.route("/add")
class PositionAdd(Resource):
    @api_key_or_jwt_required
    @admin_required
    @position_ns.expect(position_create_model, validate=False)
    @position_ns.marshal_with(position_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info("Request to add new position", extra={"login": current_user})
        schema = PositionCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(PositionCreatePayload, schema.load(raw_payload))
            position = CreatePositionUseCase(repository=_repository()).execute(
                CreatePositionCommand(
                    name=data["name"],
                    created_by=get_required_uuid(
                        current_user, "user_id", "Current user id is required"
                    ),
                )
            )
            return {
                "msg": "New position added successfully",
                "position_id": str(position.position_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error adding position: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@position_ns.route("/<string:position_id>/view")
class PositionView(Resource):
    @api_key_or_jwt_required
    @position_ns.marshal_with(position_response)
    def get(self, position_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to view position: {position_id}", extra={"login": current_user}
        )
        try:
            position = GetPositionUseCase(repository=_repository()).execute(
                _parse_position_id(position_id)
            )
            return {
                "msg": "Position found successfully",
                "position": position_entity_to_response(position),
            }, 200
        except Exception as error:
            logger.error(
                f"Error viewing position: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@position_ns.route("/<string:position_id>/edit")
class PositionEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @position_ns.expect(position_edit_model, validate=False)
    @position_ns.marshal_with(position_msg_model)
    def patch(self, position_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to edit position: {position_id}", extra={"login": current_user}
        )
        schema = PositionEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(PositionEditPayload, schema.load(raw_payload))
            if not any(value is not None for value in data.values()):
                raise ValueError("No data provided for update")
            position = UpdatePositionUseCase(repository=_repository()).execute(
                UpdatePositionCommand(
                    position_id=_parse_position_id(position_id),
                    name=get_optional_str(data, "name"),
                )
            )
            return {
                "msg": "Position updated successfully",
                "position_id": str(position.position_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error editing position: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@position_ns.route("/<string:position_id>/delete/hard")
class PositionDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @position_ns.marshal_with(position_msg_model)
    def delete(self, position_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to delete position: {position_id}", extra={"login": current_user}
        )
        try:
            deleted = DeletePositionUseCase(repository=_repository()).execute(
                _parse_position_id(position_id)
            )
            if not deleted:
                raise PositionNotFoundError("Position not found")
            return {
                "msg": f"Position {position_id} hard deleted successfully",
                "position_id": position_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error deleting position: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@position_ns.route("/all")
class PositionAll(Resource):
    @api_key_or_jwt_required
    @position_ns.expect(position_filter_parser)
    @position_ns.marshal_with(position_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all positions", extra={"login": current_user})
        schema = PositionFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            data = cast(PositionFilterPayload, schema.load(raw_args))
            positions = ListPositionsUseCase(repository=_repository()).execute(
                PositionListQuery(
                    offset=data.get("offset", 0),
                    limit=data.get("limit", 10),
                    sort_by=data.get("sort_by"),
                    sort_order=data.get("sort_order", "desc"),
                    name=get_optional_str(data, "name"),
                )
            )
            return {
                "msg": "Positions found successfully",
                "positions": [position_entity_to_response(item) for item in positions],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching positions: {error}", extra={"login": current_user}
            )
            return _map_error(error)
