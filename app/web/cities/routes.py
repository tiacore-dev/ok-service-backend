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

from app.adapters.cities import (
    SQLAlchemyCityRepository,
    city_entity_to_response,
)
from app.decorators import admin_required, api_key_or_jwt_required
from app.domain.cities import CityAlreadyExistsError, CityNotFoundError, CityValidationError
from app.schemas.city_schemas import CityCreateSchema, CityEditSchema, CityFilterSchema
from app.use_cases.cities import (
    CityListQuery,
    CreateCityCommand,
    CreateCityUseCase,
    GetCityUseCase,
    HardDeleteCityUseCase,
    ListCitiesUseCase,
    SoftDeleteCityUseCase,
    UpdateCityCommand,
    UpdateCityUseCase,
)
from app.web._typing import (
    get_optional_bool,
    get_optional_str,
    get_required_uuid,
    has_field,
    to_plain_dict,
)
from .models import (
    city_all_response,
    city_create_model,
    city_edit_model,
    city_filter_parser,
    city_model,
    city_msg_model,
    city_response,
)

logger = logging.getLogger("ok_service")

city_ns = Namespace("cities", description="City management operations")

city_ns.models[city_create_model.name] = city_create_model
city_ns.models[city_edit_model.name] = city_edit_model
city_ns.models[city_msg_model.name] = city_msg_model
city_ns.models[city_response.name] = city_response
city_ns.models[city_all_response.name] = city_all_response
city_ns.models[city_model.name] = city_model


class CityCreatePayload(TypedDict):
    name: str


class CityEditPayload(TypedDict, total=False):
    name: str | None
    deleted: bool | None


class CityFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
    name: str
    deleted: bool


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


def _repository() -> SQLAlchemyCityRepository:
    return SQLAlchemyCityRepository()


def _parse_city_id(city_id: str) -> UUID:
    return get_required_uuid({"city_id": city_id}, "city_id", "Invalid UUID format")


def _map_error(error: Exception):
    if isinstance(error, CityNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, CityAlreadyExistsError):
        return {"msg": str(error)}, 409
    if isinstance(error, CityValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete city: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@city_ns.route("/add")
class CityAdd(Resource):
    @api_key_or_jwt_required
    @admin_required
    @city_ns.expect(city_create_model)
    @city_ns.marshal_with(city_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info("Request to add new city", extra={"login": current_user})
        schema = CityCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(CityCreatePayload, schema.load(raw_payload))
            city = CreateCityUseCase(repository=_repository()).execute(
                CreateCityCommand(
                    name=data["name"],
                    created_by=get_required_uuid(
                        current_user, "user_id", "Current user id is required"
                    ),
                )
            )
            return {"msg": "New city added successfully", "city_id": str(city.city_id)}, 200
        except Exception as error:
            logger.error(f"Error adding city: {error}", extra={"login": current_user})
            return _map_error(error)


@city_ns.route("/<string:city_id>/view")
class CityView(Resource):
    @api_key_or_jwt_required
    @city_ns.marshal_with(city_response)
    def get(self, city_id):
        current_user = _get_current_user()
        logger.info(f"Request to view city: {city_id}", extra={"login": current_user})
        try:
            city = GetCityUseCase(repository=_repository()).execute(
                _parse_city_id(city_id)
            )
            return {"msg": "City found successfully", "city": city_entity_to_response(city)}, 200
        except Exception as error:
            logger.error(f"Error viewing city: {error}", extra={"login": current_user})
            return _map_error(error)


@city_ns.route("/<string:city_id>/delete/soft")
class CitySoftDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @city_ns.marshal_with(city_msg_model)
    def patch(self, city_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to soft delete city: {city_id}", extra={"login": current_user}
        )
        try:
            SoftDeleteCityUseCase(repository=_repository()).execute(
                _parse_city_id(city_id)
            )
            return {
                "msg": f"City {city_id} soft deleted successfully",
                "city_id": city_id,
            }, 200
        except Exception as error:
            logger.error(f"Error soft deleting city: {error}", extra={"login": current_user})
            return _map_error(error)


@city_ns.route("/<string:city_id>/delete/hard")
class CityHardDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @city_ns.marshal_with(city_msg_model)
    def delete(self, city_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete city: {city_id}", extra={"login": current_user}
        )
        try:
            HardDeleteCityUseCase(repository=_repository()).execute(
                _parse_city_id(city_id)
            )
            return {
                "msg": f"City {city_id} hard deleted successfully",
                "city_id": city_id,
            }, 200
        except Exception as error:
            logger.error(f"Error hard deleting city: {error}", extra={"login": current_user})
            return _map_error(error)


@city_ns.route("/<string:city_id>/edit")
class CityEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @city_ns.expect(city_edit_model)
    @city_ns.marshal_with(city_msg_model)
    def patch(self, city_id):
        current_user = _get_current_user()
        logger.info(f"Request to edit city: {city_id}", extra={"login": current_user})
        schema = CityEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(CityEditPayload, schema.load(raw_payload))
            if not has_field(data, "name") and not has_field(data, "deleted"):
                raise ValueError("No data provided for update")
            city = UpdateCityUseCase(repository=_repository()).execute(
                UpdateCityCommand(
                    city_id=_parse_city_id(city_id),
                    has_name=has_field(data, "name"),
                    name=get_optional_str(data, "name"),
                    has_deleted=has_field(data, "deleted"),
                    deleted=get_optional_bool(data, "deleted"),
                )
            )
            return {"msg": "City edited successfully", "city_id": str(city.city_id)}, 200
        except Exception as error:
            logger.error(f"Error editing city: {error}", extra={"login": current_user})
            return _map_error(error)


@city_ns.route("/all")
class CityAll(Resource):
    @api_key_or_jwt_required
    @city_ns.expect(city_filter_parser)
    @city_ns.marshal_with(city_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all cities", extra={"login": current_user})
        schema = CityFilterSchema()
        try:
            raw_args = request.args.to_dict()
            data = cast(CityFilterPayload, schema.load(raw_args))
            query = CityListQuery(
                offset=data.get("offset", 0),
                limit=data.get("limit", 1000),
                sort_by=data.get("sort_by"),
                sort_order=data.get("sort_order", "desc"),
                name=data.get("name"),
                deleted=data.get("deleted"),
            )
            cities = ListCitiesUseCase(repository=_repository()).execute(query)
            return {
                "msg": "Cities found successfully",
                "cities": [city_entity_to_response(city) for city in cities],
            }, 200
        except Exception as error:
            logger.error(f"Error fetching cities: {error}", extra={"login": current_user})
            return _map_error(error)
