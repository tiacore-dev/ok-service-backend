from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from flask import current_app, g
from flask_jwt_extended import get_jwt_identity
from flask_restx import Namespace, Resource

from app.adapters.projects import SQLAlchemyProjectRepository
from app.adapters.statistics import RedisProjectWorkStatistics
from app.decorators import api_key_or_jwt_required
from app.domain.projects import ProjectForbiddenError
from app.use_cases.projects import (
    GetProjectLeaderStatsDetailsUseCase,
    GetProjectLeaderStatsUseCase,
    ProjectActor,
)
from app.web.objects.models import object_stats_details_response, object_stats_response
from app.web._typing import get_required_uuid

project_leader_ns = Namespace(
    "project_leaders",
    description="Project leader statistics operations",
    path="/project-leaders",
)
for model in (object_stats_response, object_stats_details_response):
    project_leader_ns.models[model.name] = model


def _identity() -> dict[str, Any]:
    identity = (
        getattr(g, "api_key_identity_json", None)
        if getattr(g, "auth_via_api_key", False)
        else get_jwt_identity()
    )
    if isinstance(identity, dict):
        return identity
    if isinstance(identity, (str, bytes, bytearray)):
        try:
            parsed = json.loads(identity)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _actor() -> ProjectActor:
    identity = _identity()
    return ProjectActor(
        role=str(identity.get("role", "")),
        user_id=get_required_uuid(identity, "user_id", "Current user id is required"),
    )


def _repository() -> SQLAlchemyProjectRepository:
    return SQLAlchemyProjectRepository(
        statistics=RedisProjectWorkStatistics(current_app.extensions["redis"])
    )


def _id(value: str) -> UUID:
    return get_required_uuid(
        {"project_leader_id": value},
        "project_leader_id",
        "Invalid UUID format",
    )


def _error(error: Exception):
    if isinstance(error, ProjectForbiddenError):
        return {"msg": str(error)}, 403
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": "Internal server error"}, 500


@project_leader_ns.route("/<string:project_leader_id>/get-stat")
class ProjectLeaderStats(Resource):
    @api_key_or_jwt_required
    @project_leader_ns.marshal_with(object_stats_response)
    def get(self, project_leader_id):
        try:
            stats = GetProjectLeaderStatsUseCase(_repository()).execute(
                _id(project_leader_id), _actor()
            )
            return {"msg": "Project leader stats fetched successfully", "stats": stats}, 200
        except Exception as error:
            return _error(error)


@project_leader_ns.route("/<string:project_leader_id>/get-stat-details")
class ProjectLeaderStatsDetails(Resource):
    @api_key_or_jwt_required
    @project_leader_ns.marshal_with(object_stats_details_response)
    def get(self, project_leader_id):
        try:
            stats = GetProjectLeaderStatsDetailsUseCase(_repository()).execute(
                _id(project_leader_id), _actor()
            )
            return {
                "msg": "Project leader detailed stats fetched successfully",
                "stats": stats,
            }, 200
        except Exception as error:
            return _error(error)
