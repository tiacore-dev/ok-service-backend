from __future__ import annotations

import json
import logging
from typing import Any, NotRequired, TypedDict, cast
from uuid import UUID

from flask import g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.materials import (
    SQLAlchemyMaterialRepository,
    material_entity_to_response,
)
from app.decorators import admin_required, api_key_or_jwt_required
from app.domain.materials import MaterialNotFoundError, MaterialValidationError
from app.routes.models.material_models import (
    material_all_response,
    material_create_model,
    material_edit_model,
    material_filter_parser,
    material_model,
    material_msg_model,
    material_response,
)
from app.schemas.material_schemas import (
    MaterialCreateSchema,
    MaterialEditSchema,
    MaterialFilterSchema,
)
from app.use_cases.materials import (
    CreateMaterialCommand,
    CreateMaterialUseCase,
    DeleteMaterialUseCase,
    GetMaterialUseCase,
    ListMaterialsUseCase,
    MaterialListQuery,
    UpdateMaterialCommand,
    UpdateMaterialUseCase,
)
from app.web._typing import (
    get_optional_bool,
    get_optional_int,
    get_optional_str,
    get_required_uuid,
    to_plain_dict,
)

logger = logging.getLogger("ok_service")

material_ns = Namespace("materials", description="Materials management operations")

material_ns.models[material_create_model.name] = material_create_model
material_ns.models[material_edit_model.name] = material_edit_model
material_ns.models[material_msg_model.name] = material_msg_model
material_ns.models[material_response.name] = material_response
material_ns.models[material_all_response.name] = material_all_response
material_ns.models[material_model.name] = material_model


class MaterialCreatePayload(TypedDict):
    name: str
    measurement_unit: NotRequired[str | None]


class MaterialEditPayload(TypedDict, total=False):
    name: str
    measurement_unit: NotRequired[str | None]
    deleted: bool


class MaterialFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
    name: str
    measurement_unit: str
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


def _repository() -> SQLAlchemyMaterialRepository:
    return SQLAlchemyMaterialRepository()


def _parse_material_id(material_id: str) -> UUID:
    try:
        return UUID(material_id)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _map_error(error: Exception):
    if isinstance(error, MaterialNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, MaterialValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete material: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@material_ns.route("/add")
class MaterialAdd(Resource):
    @api_key_or_jwt_required
    @admin_required
    @material_ns.expect(material_create_model, validate=False)
    @material_ns.marshal_with(material_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info("Request to add new material", extra={"login": current_user})

        schema = MaterialCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(MaterialCreatePayload, schema.load(raw_payload))
            material = CreateMaterialUseCase(repository=_repository()).execute(
                CreateMaterialCommand(
                    name=data["name"],
                    measurement_unit=get_optional_str(data, "measurement_unit"),
                    created_by=get_required_uuid(
                        current_user, "user_id", "Current user id is required"
                    ),
                )
            )
            return {
                "msg": "New material added successfully",
                "material_id": str(material.material_id),
            }, 200
        except Exception as error:
            logger.error(f"Error adding material: {error}", extra={"login": current_user})
            return _map_error(error)


@material_ns.route("/<string:material_id>/view")
class MaterialView(Resource):
    @api_key_or_jwt_required
    @material_ns.marshal_with(material_response)
    def get(self, material_id):
        current_user = _get_current_user()
        logger.info(f"Request to view material: {material_id}", extra={"login": current_user})
        try:
            material = GetMaterialUseCase(repository=_repository()).execute(
                _parse_material_id(material_id)
            )
            return {
                "msg": "Material found successfully",
                "material": material_entity_to_response(material),
            }, 200
        except Exception as error:
            logger.error(f"Error viewing material: {error}", extra={"login": current_user})
            return _map_error(error)


@material_ns.route("/<string:material_id>/delete/soft")
class MaterialSoftDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @material_ns.marshal_with(material_msg_model)
    def patch(self, material_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to soft delete material: {material_id}", extra={"login": current_user}
        )
        try:
            material = UpdateMaterialUseCase(repository=_repository()).execute(
                UpdateMaterialCommand(
                    material_id=_parse_material_id(material_id),
                    deleted=True,
                )
            )
            return {
                "msg": f"Material {material.material_id} soft deleted successfully",
                "material_id": str(material.material_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error soft deleting material: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@material_ns.route("/<string:material_id>/delete/hard")
class MaterialHardDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @material_ns.marshal_with(material_msg_model)
    def delete(self, material_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete material: {material_id}", extra={"login": current_user}
        )
        try:
            deleted = DeleteMaterialUseCase(repository=_repository()).execute(
                _parse_material_id(material_id)
            )
            if not deleted:
                raise MaterialNotFoundError("Material not found")
            return {
                "msg": f"Material {material_id} hard deleted successfully",
                "material_id": material_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error hard deleting material: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@material_ns.route("/<string:material_id>/edit")
class MaterialEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @material_ns.expect(material_edit_model, validate=False)
    @material_ns.marshal_with(material_msg_model)
    def patch(self, material_id):
        current_user = _get_current_user()
        logger.info(f"Request to edit material: {material_id}", extra={"login": current_user})

        schema = MaterialEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(MaterialEditPayload, schema.load(raw_payload))
            material = UpdateMaterialUseCase(repository=_repository()).execute(
                UpdateMaterialCommand(
                    material_id=_parse_material_id(material_id),
                    name=get_optional_str(data, "name"),
                    measurement_unit=get_optional_str(data, "measurement_unit"),
                    deleted=get_optional_bool(data, "deleted"),
                )
            )
            return {
                "msg": "Material edited successfully",
                "material_id": str(material.material_id),
            }, 200
        except Exception as error:
            logger.error(f"Error editing material: {error}", extra={"login": current_user})
            return _map_error(error)


@material_ns.route("/all")
class MaterialAll(Resource):
    @api_key_or_jwt_required
    @material_ns.expect(material_filter_parser)
    @material_ns.marshal_with(material_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all materials", extra={"login": current_user})

        schema = MaterialFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            args = cast(MaterialFilterPayload, schema.load(raw_args))
            query = MaterialListQuery(
                offset=get_optional_int(args, "offset") or 0,
                limit=get_optional_int(args, "limit"),
                sort_by=get_optional_str(args, "sort_by") or "created_at",
                sort_order=get_optional_str(args, "sort_order") or "desc",
                name=get_optional_str(args, "name"),
                measurement_unit=get_optional_str(args, "measurement_unit"),
                deleted=get_optional_bool(args, "deleted"),
            )
            materials = ListMaterialsUseCase(repository=_repository()).execute(query)
            return {
                "msg": "Materials found successfully",
                "materials": [material_entity_to_response(item) for item in materials],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching materials: {error}", extra={"login": current_user}
            )
            return _map_error(error)
