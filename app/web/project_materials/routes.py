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

from app.adapters.project_materials import (
    SQLAlchemyProjectMaterialRepository,
    project_material_entity_to_response,
)
from app.decorators import admin_required, api_key_or_jwt_required
from app.domain.project_materials import (
    ProjectMaterialForbiddenError,
    ProjectMaterialNotFoundError,
    ProjectMaterialValidationError,
)
from app.routes.models.project_material_models import (
    project_material_all_response,
    project_material_create_model,
    project_material_edit_model,
    project_material_filter_parser,
    project_material_model,
    project_material_msg_model,
    project_material_response,
)
from app.schemas.project_material_schemas import (
    ProjectMaterialCreateSchema,
    ProjectMaterialEditSchema,
    ProjectMaterialFilterSchema,
)
from app.use_cases.project_materials import (
    CreateProjectMaterialCommand,
    CreateProjectMaterialUseCase,
    DeleteProjectMaterialUseCase,
    GetProjectMaterialUseCase,
    ListProjectMaterialsUseCase,
    ProjectMaterialActor,
    ProjectMaterialListQuery,
    UpdateProjectMaterialCommand,
    UpdateProjectMaterialUseCase,
)
from app.web._typing import (
    get_optional_decimal,
    get_optional_int,
    get_optional_str,
    get_optional_uuid,
    get_required_decimal,
    get_required_uuid,
    has_field,
    to_plain_dict,
)

logger = logging.getLogger("ok_service")

project_material_ns = Namespace(
    "project_materials", description="Project materials management operations"
)

project_material_ns.models[project_material_create_model.name] = (
    project_material_create_model
)
project_material_ns.models[project_material_msg_model.name] = project_material_msg_model
project_material_ns.models[project_material_response.name] = project_material_response
project_material_ns.models[project_material_all_response.name] = (
    project_material_all_response
)
project_material_ns.models[project_material_model.name] = project_material_model
project_material_ns.models[project_material_edit_model.name] = (
    project_material_edit_model
)


class ProjectMaterialCreatePayload(TypedDict):
    project: str
    material: str
    quantity: float | int
    project_work: str | None


class ProjectMaterialEditPayload(TypedDict, total=False):
    project: str
    material: str
    quantity: float | int
    project_work: str | None


class ProjectMaterialFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    project: str
    material: str
    project_work: str
    sort_by: str
    sort_order: str


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


def _repository() -> SQLAlchemyProjectMaterialRepository:
    return SQLAlchemyProjectMaterialRepository()


def _parse_project_material_id(project_material_id: str) -> UUID:
    try:
        return UUID(project_material_id)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _map_error(error: Exception):
    if isinstance(error, ProjectMaterialNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, ProjectMaterialForbiddenError):
        return {"msg": str(error)}, 403
    if isinstance(error, ProjectMaterialValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete project material: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@project_material_ns.route("/add")
class ProjectMaterialAdd(Resource):
    @api_key_or_jwt_required
    @project_material_ns.expect(project_material_create_model)
    @project_material_ns.marshal_with(project_material_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info(
            "Request to add new project material", extra={"login": current_user}
        )

        schema = ProjectMaterialCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(ProjectMaterialCreatePayload, schema.load(raw_payload))
            command = CreateProjectMaterialCommand(
                project=get_required_uuid(data, "project", "Project is required"),
                material=get_required_uuid(data, "material", "Material is required"),
                quantity=get_required_decimal(data, "quantity", "Quantity is required"),
                project_work=get_optional_uuid(data, "project_work"),
                created_by=get_required_uuid(
                    current_user, "user_id", "Current user id is required"
                ),
            )
            record = CreateProjectMaterialUseCase(repository=_repository()).execute(
                command,
                ProjectMaterialActor(
                    role=(
                        "admin"
                        if getattr(g, "auth_via_api_key", False)
                        else str(current_user.get("role", ""))
                    ),
                    user_id=command.created_by,
                ),
            )
            return {
                "msg": "Project material added successfully",
                "project_material_id": str(record.project_material_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error adding project material: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_material_ns.route("/<string:project_material_id>/view")
class ProjectMaterialView(Resource):
    @api_key_or_jwt_required
    @project_material_ns.marshal_with(project_material_response)
    def get(self, project_material_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to view project material: {project_material_id}",
            extra={"login": current_user},
        )
        try:
            record = GetProjectMaterialUseCase(repository=_repository()).execute(
                _parse_project_material_id(project_material_id)
            )
            return {
                "msg": "Project material found successfully",
                "project_material": project_material_entity_to_response(record),
            }, 200
        except Exception as error:
            logger.error(
                f"Error viewing project material: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@project_material_ns.route("/<string:project_material_id>/delete/hard")
class ProjectMaterialHardDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @project_material_ns.marshal_with(project_material_msg_model)
    def delete(self, project_material_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete project material: {project_material_id}",
            extra={"login": current_user},
        )
        try:
            deleted = DeleteProjectMaterialUseCase(repository=_repository()).execute(
                _parse_project_material_id(project_material_id)
            )
            if not deleted:
                raise ProjectMaterialNotFoundError("Project material not found")
            return {
                "msg": f"Project material {
                    project_material_id
                } hard deleted successfully",
                "project_material_id": project_material_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error hard deleting project material: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@project_material_ns.route("/<string:project_material_id>/edit")
class ProjectMaterialEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @project_material_ns.expect(project_material_edit_model, validate=False)
    @project_material_ns.marshal_with(project_material_msg_model)
    def patch(self, project_material_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to edit project material: {project_material_id}",
            extra={"login": current_user},
        )

        schema = ProjectMaterialEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(ProjectMaterialEditPayload, schema.load(raw_payload))
            record = UpdateProjectMaterialUseCase(repository=_repository()).execute(
                UpdateProjectMaterialCommand(
                    project_material_id=_parse_project_material_id(project_material_id),
                    project=get_optional_uuid(data, "project"),
                    project_is_set=has_field(data, "project"),
                    material=get_optional_uuid(data, "material"),
                    material_is_set=has_field(data, "material"),
                    quantity=get_optional_decimal(data, "quantity"),
                    quantity_is_set=has_field(data, "quantity"),
                    project_work=get_optional_uuid(data, "project_work"),
                    project_work_is_set=has_field(data, "project_work"),
                )
            )
            return {
                "msg": "Project material edited successfully",
                "project_material_id": str(record.project_material_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error editing project material: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@project_material_ns.route("/all")
class ProjectMaterialAll(Resource):
    @api_key_or_jwt_required
    @project_material_ns.expect(project_material_filter_parser)
    @project_material_ns.marshal_with(project_material_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info(
            "Request to fetch all project materials", extra={"login": current_user}
        )

        schema = ProjectMaterialFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            args = cast(ProjectMaterialFilterPayload, schema.load(raw_args))
            query = ProjectMaterialListQuery(
                offset=get_optional_int(args, "offset") or 0,
                limit=get_optional_int(args, "limit"),
                sort_by=get_optional_str(args, "sort_by") or "created_at",
                sort_order=get_optional_str(args, "sort_order") or "desc",
                project=get_optional_uuid(args, "project"),
                material=get_optional_uuid(args, "material"),
                project_work=get_optional_uuid(args, "project_work"),
            )
            records = ListProjectMaterialsUseCase(repository=_repository()).execute(
                query
            )
            return {
                "msg": "Project materials found successfully",
                "project_materials": [
                    project_material_entity_to_response(item) for item in records
                ],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching project materials: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)
