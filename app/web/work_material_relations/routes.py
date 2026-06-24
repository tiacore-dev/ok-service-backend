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

from app.adapters.work_material_relations import (
    SQLAlchemyWorkMaterialRelationRepository,
    work_material_relation_entity_to_response,
)
from app.decorators import admin_required, api_key_or_jwt_required
from app.domain.work_material_relations import (
    WorkMaterialRelationNotFoundError,
    WorkMaterialRelationValidationError,
)
from app.routes.models.work_material_relation_models import (
    work_material_relation_all_response,
    work_material_relation_create_model,
    work_material_relation_edit_model,
    work_material_relation_filter_parser,
    work_material_relation_model,
    work_material_relation_msg_model,
    work_material_relation_response,
)
from app.schemas.work_material_relation_schemas import (
    WorkMaterialRelationCreateSchema,
    WorkMaterialRelationEditSchema,
    WorkMaterialRelationFilterSchema,
)
from app.use_cases.work_material_relations import (
    CreateWorkMaterialRelationCommand,
    CreateWorkMaterialRelationUseCase,
    DeleteWorkMaterialRelationUseCase,
    GetWorkMaterialRelationUseCase,
    ListWorkMaterialRelationsUseCase,
    UpdateWorkMaterialRelationCommand,
    UpdateWorkMaterialRelationUseCase,
    WorkMaterialRelationListQuery,
)
from app.web._typing import (
    get_optional_decimal,
    get_optional_int,
    get_optional_str,
    get_required_decimal,
    get_required_uuid,
    optional_uuid,
    to_plain_dict,
)

logger = logging.getLogger("ok_service")

work_material_relation_ns = Namespace(
    "work_material_relations",
    description="Work material relations management operations",
)

work_material_relation_ns.models[work_material_relation_create_model.name] = (
    work_material_relation_create_model
)
work_material_relation_ns.models[work_material_relation_edit_model.name] = (
    work_material_relation_edit_model
)
work_material_relation_ns.models[work_material_relation_msg_model.name] = (
    work_material_relation_msg_model
)
work_material_relation_ns.models[work_material_relation_response.name] = (
    work_material_relation_response
)
work_material_relation_ns.models[work_material_relation_all_response.name] = (
    work_material_relation_all_response
)
work_material_relation_ns.models[work_material_relation_model.name] = (
    work_material_relation_model
)


class WorkMaterialRelationCreatePayload(TypedDict):
    work: str
    material: str
    quantity: float


class WorkMaterialRelationEditPayload(TypedDict, total=False):
    work: str
    material: str
    quantity: float


class WorkMaterialRelationFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
    work: str
    material: str
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


def _repository() -> SQLAlchemyWorkMaterialRelationRepository:
    return SQLAlchemyWorkMaterialRelationRepository()


def _parse_relation_id(relation_id: str) -> UUID:
    try:
        return UUID(relation_id)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _map_error(error: Exception):
    if isinstance(error, WorkMaterialRelationNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, WorkMaterialRelationValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete work material relation: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@work_material_relation_ns.route("/add")
class WorkMaterialRelationAdd(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_material_relation_ns.expect(work_material_relation_create_model, validate=False)
    @work_material_relation_ns.marshal_with(work_material_relation_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info(
            "Request to add new work material relation",
            extra={"login": current_user},
        )
        schema = WorkMaterialRelationCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(WorkMaterialRelationCreatePayload, schema.load(raw_payload))
            relation = CreateWorkMaterialRelationUseCase(repository=_repository()).execute(
                CreateWorkMaterialRelationCommand(
                    work=get_required_uuid(data, "work", "Work is required"),
                    material=get_required_uuid(data, "material", "Material is required"),
                    quantity=get_required_decimal(
                        data, "quantity", "Quantity is required"
                    ),
                    created_by=get_required_uuid(
                        current_user, "user_id", "Current user id is required"
                    ),
                )
            )
            return {
                "msg": "Work material relation added successfully",
                "work_material_relation_id": str(relation.work_material_relation_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error adding work material relation: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@work_material_relation_ns.route("/<string:relation_id>/view")
class WorkMaterialRelationView(Resource):
    @api_key_or_jwt_required
    @work_material_relation_ns.marshal_with(work_material_relation_response)
    def get(self, relation_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to view work material relation: {relation_id}",
            extra={"login": current_user},
        )
        try:
            relation = GetWorkMaterialRelationUseCase(repository=_repository()).execute(
                _parse_relation_id(relation_id)
            )
            return {
                "msg": "Work material relation found successfully",
                "work_material_relation": work_material_relation_entity_to_response(
                    relation
                ),
            }, 200
        except Exception as error:
            logger.error(
                f"Error viewing work material relation: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@work_material_relation_ns.route("/<string:relation_id>/delete/hard")
class WorkMaterialRelationHardDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_material_relation_ns.marshal_with(work_material_relation_msg_model)
    def delete(self, relation_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete work material relation: {relation_id}",
            extra={"login": current_user},
        )
        try:
            deleted = DeleteWorkMaterialRelationUseCase(repository=_repository()).execute(
                _parse_relation_id(relation_id)
            )
            if not deleted:
                raise WorkMaterialRelationNotFoundError("Work material relation not found")
            return {
                "msg": f"Work material relation {relation_id} hard deleted successfully",
                "work_material_relation_id": relation_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error hard deleting work material relation: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@work_material_relation_ns.route("/<string:relation_id>/edit")
class WorkMaterialRelationEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_material_relation_ns.expect(work_material_relation_edit_model, validate=False)
    @work_material_relation_ns.marshal_with(work_material_relation_msg_model)
    def patch(self, relation_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to edit work material relation: {relation_id}",
            extra={"login": current_user},
        )

        schema = WorkMaterialRelationEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(WorkMaterialRelationEditPayload, schema.load(raw_payload))
            relation = UpdateWorkMaterialRelationUseCase(
                repository=_repository()
            ).execute(
                UpdateWorkMaterialRelationCommand(
                    work_material_relation_id=_parse_relation_id(relation_id),
                    work=optional_uuid(get_optional_str(data, "work")),
                    material=optional_uuid(get_optional_str(data, "material")),
                    quantity=get_optional_decimal(data, "quantity"),
                )
            )
            return {
                "msg": "Work material relation edited successfully",
                "work_material_relation_id": str(relation.work_material_relation_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error editing work material relation: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@work_material_relation_ns.route("/all")
class WorkMaterialRelationAll(Resource):
    @api_key_or_jwt_required
    @work_material_relation_ns.expect(work_material_relation_filter_parser)
    @work_material_relation_ns.marshal_with(work_material_relation_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info(
            "Request to fetch all work material relations",
            extra={"login": current_user},
        )

        schema = WorkMaterialRelationFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            args = cast(WorkMaterialRelationFilterPayload, schema.load(raw_args))
            query = WorkMaterialRelationListQuery(
                offset=get_optional_int(args, "offset") or 0,
                limit=get_optional_int(args, "limit"),
                sort_by=get_optional_str(args, "sort_by") or "created_at",
                sort_order=get_optional_str(args, "sort_order") or "desc",
                work=optional_uuid(get_optional_str(args, "work")),
                material=optional_uuid(get_optional_str(args, "material")),
            )
            relations = ListWorkMaterialRelationsUseCase(repository=_repository()).execute(
                query
            )
            return {
                "msg": "Work material relations found successfully",
                "work_material_relations": [
                    work_material_relation_entity_to_response(item)
                    for item in relations
                ],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching work material relations: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)
