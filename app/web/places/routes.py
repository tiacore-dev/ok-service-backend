from __future__ import annotations

import json
from typing import Any, TypedDict, cast
from uuid import UUID

from flask import g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.attachments import list_attachment_view_data
from app.adapters.places import SQLAlchemyPlaceRepository
from app.decorators import admin_required, api_key_or_jwt_required
from app.domain.places import PlaceForbiddenError, PlaceNotFoundError, PlaceValidationError
from app.schemas.place_schemas import PlaceCreateSchema, PlaceEditSchema
from app.use_cases.places import (
    CreatePlaceCommand,
    CreatePlaceUseCase,
    GetPlaceUseCase,
    HardDeletePlaceUseCase,
    ListPlacesUseCase,
    PlaceActor,
    SoftDeletePlaceUseCase,
    UpdatePlaceCommand,
    UpdatePlaceUseCase,
)
from app.adapters.place_relations import SQLAlchemyPlaceRelationRepository
from app.use_cases.place_relations import PlaceRelationConflictError
from app.web._typing import to_plain_dict

from app.routes.models.place_models import (
    place_all_response,
    place_create_model,
    place_edit_model,
    place_model,
    place_msg_model,
    place_response,
    place_view_model,
)
from app.web.attachments.contract import attachment_view_model

place_ns = Namespace("places", description="Places management operations")
for model in (
    place_create_model,
    place_edit_model,
    place_model,
    place_msg_model,
    place_response,
    place_all_response,
    place_view_model,
):
    place_ns.models[model.name] = model
place_ns.models[attachment_view_model.name] = attachment_view_model


class PlaceCreatePayload(TypedDict):
    object_id: UUID
    name: str
    description: str | None


class PlaceEditPayload(TypedDict, total=False):
    object_id: UUID
    name: str
    description: str | None
    deleted: bool


def _identity() -> dict[str, Any]:
    value = (
        getattr(g, "api_key_identity_json", None)
        if getattr(g, "auth_via_api_key", False)
        else _get_jwt_identity()
    )
    if isinstance(value, dict):
        return value
    if isinstance(value, (str, bytes, bytearray)):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _actor() -> PlaceActor:
    return PlaceActor(role=str(_identity().get("role", "")))


def _parse_id(place_id: str) -> UUID:
    try:
        return UUID(place_id)
    except ValueError as error:
        raise ValueError("Invalid UUID format") from error


def _response(place) -> dict[str, Any]:
    return {
        "place_id": str(place.place_id),
        "object_id": str(place.object_id),
        "name": place.name,
        "description": place.description,
        "deleted": place.deleted,
    }


def _error(error: Exception):
    if isinstance(error, PlaceRelationConflictError):
        return {"msg": str(error)}, 409
    if isinstance(error, PlaceNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, PlaceForbiddenError):
        return {"msg": str(error)}, 403
    if isinstance(error, PlaceValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete place: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@place_ns.route("/add")
class PlaceAdd(Resource):
    @api_key_or_jwt_required
    @admin_required
    @place_ns.expect(place_create_model)
    @place_ns.marshal_with(place_msg_model)
    def post(self):
        try:
            data = cast(
                PlaceCreatePayload,
                PlaceCreateSchema().load(
                    to_plain_dict(request.get_json(silent=True), "Request body is required")
                ),
            )
            place = CreatePlaceUseCase(SQLAlchemyPlaceRepository()).execute(
                CreatePlaceCommand(
                    object_id=data["object_id"],
                    name=data["name"],
                    description=data.get("description"),
                ),
                _actor(),
            )
            return {"msg": "New place added successfully", "place_id": str(place.place_id)}, 200
        except Exception as error:
            return _error(error)


@place_ns.route("/<string:place_id>/view")
class PlaceView(Resource):
    @api_key_or_jwt_required
    @place_ns.marshal_with(place_response)
    def get(self, place_id):
        try:
            place = GetPlaceUseCase(SQLAlchemyPlaceRepository()).execute(_parse_id(place_id), _actor())
            place_response_data = _response(place)
            place_response_data["attachments"] = list_attachment_view_data(
                "place", place.place_id
            )
            return {"msg": "Place found successfully", "place": place_response_data}, 200
        except Exception as error:
            return _error(error)


@place_ns.route("/<string:place_id>/edit")
class PlaceEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @place_ns.expect(place_edit_model)
    @place_ns.marshal_with(place_msg_model)
    def patch(self, place_id):
        try:
            data = cast(
                PlaceEditPayload,
                PlaceEditSchema().load(
                    to_plain_dict(request.get_json(silent=True), "Request body is required")
                ),
            )
            if not data:
                raise ValueError("No data provided for update")
            object_id = data.get("object_id")
            if object_id is not None:
                SQLAlchemyPlaceRelationRepository().ensure_place_object(
                    _parse_id(place_id), object_id
                )
            place = UpdatePlaceUseCase(SQLAlchemyPlaceRepository()).execute(
                UpdatePlaceCommand(
                    place_id=_parse_id(place_id),
                    object_id=data.get("object_id"),
                    name=data.get("name"),
                    description=data.get("description"),
                    deleted=data.get("deleted"),
                ),
                _actor(),
            )
            return {"msg": "Place edited successfully", "place_id": str(place.place_id)}, 200
        except Exception as error:
            return _error(error)


@place_ns.route("/<string:place_id>/delete/soft")
class PlaceSoftDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @place_ns.marshal_with(place_msg_model)
    def patch(self, place_id):
        try:
            place = SoftDeletePlaceUseCase(SQLAlchemyPlaceRepository()).execute(
                _parse_id(place_id), _actor()
            )
            return {
                "msg": f"Place {place_id} soft deleted successfully",
                "place_id": str(place.place_id),
            }, 200
        except Exception as error:
            return _error(error)


@place_ns.route("/<string:place_id>/delete/hard")
class PlaceHardDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @place_ns.marshal_with(place_msg_model)
    def delete(self, place_id):
        try:
            HardDeletePlaceUseCase(SQLAlchemyPlaceRepository()).execute(
                _parse_id(place_id), _actor()
            )
            return {
                "msg": f"Place {place_id} hard deleted successfully",
                "place_id": place_id,
            }, 200
        except Exception as error:
            return _error(error)


@place_ns.route("/all")
class PlaceAll(Resource):
    @api_key_or_jwt_required
    @place_ns.marshal_with(place_all_response)
    def get(self):
        try:
            places = ListPlacesUseCase(SQLAlchemyPlaceRepository()).execute(_actor())
            return {
                "msg": "Places found successfully",
                "places": [_response(place) for place in places],
            }, 200
        except Exception as error:
            return _error(error)
