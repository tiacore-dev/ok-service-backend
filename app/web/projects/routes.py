from __future__ import annotations

import json
import logging
from typing import Any, TypedDict, cast
from uuid import UUID

from flask import current_app, g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.projects import (
    SQLAlchemyProjectRepository,
    project_dict_to_response,
)
from app.adapters.attachments import list_attachment_view_data
from app.web.attachments.contract import attachment_view_model
from app.adapters.place_relations import SQLAlchemyPlaceRelationRepository
from app.use_cases.place_relations import PlaceRelationConflictError
from app.adapters.statistics import RedisProjectWorkStatistics
from app.decorators import api_key_or_jwt_required, user_forbidden
from app.domain.projects import (
    ProjectForbiddenError,
    ProjectConflictError,
    ProjectNotFoundError,
    ProjectStatus,
    ProjectValidationError,
)
from app.schemas.project_schemas import (
    ProjectCreateSchema,
    ProjectEditSchema,
    ProjectFilterSchema,
)
from app.use_cases.projects import (
    CreateProjectCommand,
    CreateProjectUseCase,
    GetProjectStatsByMaterialsUseCase,
    GetProjectStatsUseCase,
    GetProjectUseCase,
    HardDeleteProjectUseCase,
    ListProjectsUseCase,
    ProjectActor,
    ProjectListQuery,
    SoftDeleteProjectUseCase,
    UpdateProjectCommand,
    UpdateProjectUseCase,
    UpdateProjectStatusUseCase,
)
from app.web._typing import (
    get_optional_bool,
    get_optional_str,
    get_optional_uuid,
    get_required_uuid,
    to_plain_dict,
)

from .models import (
    project_all_response,
    project_create_model,
    project_edit_model,
    project_filter_parser,
    project_model,
    project_msg_model,
    project_response,
    project_view_model,
    project_stats_model,
    project_stats_response,
    project_status_model,
    project_status_item_model,
    project_statuses_response,
)

logger = logging.getLogger("ok_service")

project_ns = Namespace("projects", description="Projects management operations")

project_ns.models[project_create_model.name] = project_create_model
project_ns.models[project_edit_model.name] = project_edit_model
project_ns.models[project_msg_model.name] = project_msg_model
project_ns.models[project_response.name] = project_response
project_ns.models[project_all_response.name] = project_all_response
project_ns.models[project_model.name] = project_model
project_ns.models[project_view_model.name] = project_view_model
project_ns.models[project_stats_model.name] = project_stats_model
project_ns.models[project_stats_response.name] = project_stats_response
project_ns.models[project_status_model.name] = project_status_model
project_ns.models[project_status_item_model.name] = project_status_item_model
project_ns.models[project_statuses_response.name] = project_statuses_response
project_ns.models[attachment_view_model.name] = attachment_view_model


class ProjectCreatePayload(TypedDict):
    name: str
    object: str
    project_leader: str | None
    night_shift_available: bool | None
    extreme_conditions_available: bool | None


class ProjectEditPayload(TypedDict, total=False):
    name: str | None
    object: str | None
    project_leader: str | None
    night_shift_available: bool | None
    extreme_conditions_available: bool | None
    deleted: bool | None


class ProjectFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
    object: str
    project_leader: str
    created_by: str
    name: str
    created_at: int
    night_shift_available: bool
    extreme_conditions_available: bool
    deleted: bool
    status: str


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


def _repository() -> SQLAlchemyProjectRepository:
    return SQLAlchemyProjectRepository(
        statistics=RedisProjectWorkStatistics(current_app.extensions["redis"])
    )


def _parse_project_id(project_id: str) -> UUID:
    return get_required_uuid(
        {"project_id": project_id}, "project_id", "Invalid UUID format"
    )


def _actor(current_user: dict[str, Any]) -> ProjectActor:
    return ProjectActor(
        role=str(current_user.get("role", "")),
        user_id=get_required_uuid(
            current_user, "user_id", "Current user id is required"
        ),
    )


def _map_error(error: Exception):
    if isinstance(error, PlaceRelationConflictError):
        return {"msg": str(error)}, 409
    if isinstance(error, ProjectNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, ProjectConflictError):
        return {"msg": str(error)}, 409
    if isinstance(error, ProjectForbiddenError):
        return {"msg": str(error)}, 403
    if isinstance(error, ProjectValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete project: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@project_ns.route("/add")
class ProjectAdd(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_ns.expect(project_create_model)
    @project_ns.marshal_with(project_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info("Request to add new project", extra={"login": current_user})
        schema = ProjectCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(ProjectCreatePayload, schema.load(raw_payload))
            project = CreateProjectUseCase(repository=_repository()).execute(
                CreateProjectCommand(
                    name=data["name"],
                    object=get_required_uuid(data, "object", "Object is required"),
                    project_leader=get_optional_uuid(data, "project_leader"),
                    night_shift_available=bool(
                        get_optional_bool(data, "night_shift_available")
                    ),
                    extreme_conditions_available=bool(
                        get_optional_bool(data, "extreme_conditions_available")
                    ),
                    created_by=get_required_uuid(
                        current_user, "user_id", "Current user id is required"
                    ),
                ),
                _actor(current_user),
            )
            return {
                "msg": "New project added successfully",
                "project_id": str(project.project_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error adding project: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_ns.route("/<string:project_id>/view")
class ProjectView(Resource):
    @api_key_or_jwt_required
    @project_ns.marshal_with(project_response)
    def get(self, project_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to view project: {project_id}", extra={"login": current_user}
        )
        try:
            project = GetProjectUseCase(repository=_repository()).execute(
                _parse_project_id(project_id), _actor(current_user)
            )
            places = [
                SQLAlchemyPlaceRelationRepository().place_response(item.place_id)
                for item in SQLAlchemyPlaceRelationRepository().list_project_place_relations()
                if item.project_id == _parse_project_id(project_id)
            ]
            project_response_data = project_dict_to_response(project)
            project_response_data["places"] = [item for item in places if item is not None]
            project_response_data["attachments"] = list_attachment_view_data(
                "project", _parse_project_id(project_id)
            )
            return {
                "msg": "Project found successfully",
                "project": project_response_data,
            }, 200
        except Exception as error:
            logger.error(
                f"Error viewing project: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_ns.route("/<string:project_id>/delete/soft")
class ProjectSoftDelete(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_ns.marshal_with(project_msg_model)
    def patch(self, project_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to soft delete project: {project_id}",
            extra={"login": current_user},
        )
        try:
            SoftDeleteProjectUseCase(repository=_repository()).execute(
                _parse_project_id(project_id),
                _actor(current_user),
            )
            return {
                "msg": f"Project {project_id} soft deleted successfully",
                "project_id": project_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error soft deleting project: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_ns.route("/<string:project_id>/delete/hard")
class ProjectHardDelete(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_ns.marshal_with(project_msg_model)
    def delete(self, project_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete project: {project_id}",
            extra={"login": current_user},
        )
        try:
            HardDeleteProjectUseCase(repository=_repository()).execute(
                _parse_project_id(project_id),
                _actor(current_user),
            )
            return {
                "msg": f"Project {project_id} hard deleted successfully",
                "project_id": project_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error hard deleting project: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_ns.route("/<string:project_id>/edit")
class ProjectEdit(Resource):
    @api_key_or_jwt_required
    @user_forbidden
    @project_ns.expect(project_edit_model)
    @project_ns.marshal_with(project_msg_model)
    def patch(self, project_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to edit project: {project_id}", extra={"login": current_user}
        )
        schema = ProjectEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(ProjectEditPayload, schema.load(raw_payload))
            if not any(value is not None for value in data.values()):
                raise ValueError("No data provided for update")
            new_object = get_optional_uuid(data, "object")
            if new_object is not None:
                SQLAlchemyPlaceRelationRepository().ensure_project_object(
                    _parse_project_id(project_id), new_object
                )
            project = UpdateProjectUseCase(repository=_repository()).execute(
                UpdateProjectCommand(
                    project_id=_parse_project_id(project_id),
                    name=data.get("name"),
                    object=get_optional_uuid(data, "object"),
                    project_leader=get_optional_uuid(data, "project_leader"),
                    night_shift_available=get_optional_bool(
                        data, "night_shift_available"
                    ),
                    extreme_conditions_available=get_optional_bool(
                        data, "extreme_conditions_available"
                    ),
                    deleted=get_optional_bool(data, "deleted"),
                ),
                _actor(current_user),
            )
            return {
                "msg": "Project edited successfully",
                "project_id": str(project.project_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error editing project: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_ns.route("/all")
class ProjectAll(Resource):
    @api_key_or_jwt_required
    @project_ns.expect(project_filter_parser)
    @project_ns.marshal_with(project_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all projects", extra={"login": current_user})
        schema = ProjectFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            data = cast(ProjectFilterPayload, schema.load(raw_args))
            status_value = data.get("status")
            projects = ListProjectsUseCase(repository=_repository()).execute(
                ProjectListQuery(
                    offset=data.get("offset", 0),
                    limit=data.get("limit", 10),
                    sort_by=data.get("sort_by"),
                    sort_order=data.get("sort_order", "desc"),
                    name=data.get("name"),
                    deleted=data.get("deleted"),
                    object=get_optional_uuid(data, "object"),
                    project_leader=get_optional_uuid(data, "project_leader"),
                    created_by=get_optional_uuid(data, "created_by"),
                    created_at=data.get("created_at"),
                    status=ProjectStatus(status_value) if status_value is not None else None,
                ),
                _actor(current_user),
            )
            return {
                "msg": "Projects found successfully",
                "projects": [
                    project_dict_to_response(project) for project in projects
                ],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching projects: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@project_ns.route("/statuses")
class ProjectStatuses(Resource):
    @api_key_or_jwt_required
    @project_ns.marshal_with(project_statuses_response)
    def get(self):
        return {
            "msg": "Project statuses found successfully",
            "statuses": [
                {"value": status.value, "label": status.label}
                for status in ProjectStatus
            ],
        }, 200


@project_ns.route("/<string:project_id>/status")
class ProjectStatusUpdate(Resource):
    @api_key_or_jwt_required
    @project_ns.expect(project_status_model)
    @project_ns.marshal_with(project_msg_model)
    def patch(self, project_id):
        current_user = _get_current_user()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            raw_status = get_optional_str(raw_payload, "status")
            if raw_status is None:
                raise ValueError("Field 'status' is required")
            status = ProjectStatus(raw_status)
            project = UpdateProjectStatusUseCase(repository=_repository()).execute(
                _parse_project_id(project_id), status, _actor(current_user)
            )
            return {
                "msg": "Project status updated successfully",
                "project_id": str(project.project_id),
            }, 200
        except (TypeError, ValueError) as error:
            return _map_error(error)
        except Exception as error:
            return _map_error(error)


@project_ns.route("/<string:project_id>/get-stat")
class ProjectStats(Resource):
    @api_key_or_jwt_required
    @project_ns.marshal_with(project_stats_response)
    def get(self, project_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to view stats of project: {project_id}",
            extra={"login": current_user},
        )
        try:
            stats = GetProjectStatsUseCase(repository=_repository()).execute(
                _parse_project_id(project_id), _actor(current_user)
            )
            return {"msg": "Project stats fetched successfully", "stats": stats}, 200
        except Exception as error:
            logger.error(
                f"Error getting stats for project: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@project_ns.route("/<string:project_id>/get-stat-by-project-materials")
class ProjectStatsByProjectMaterials(Resource):
    @api_key_or_jwt_required
    @project_ns.marshal_with(project_stats_response)
    def get(self, project_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to get project stats BY PROJECT MATERIALS for project: {
                project_id
            }",
            extra={"login": current_user},
        )
        try:
            stats = GetProjectStatsByMaterialsUseCase(repository=_repository()).execute(
                _parse_project_id(project_id), _actor(current_user)
            )
            return {"msg": "Project stats fetched successfully", "stats": stats}, 200
        except Exception as error:
            logger.error(
                f"Error getting stats for project materials: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)
