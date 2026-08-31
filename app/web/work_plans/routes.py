from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any, NotRequired, TypedDict, cast
from uuid import UUID

from flask import g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.work_plans import (
    SQLAlchemyWorkPlanRepository,
    work_plan_entity_to_response,
)
from app.decorators import admin_or_manager_required, api_key_or_jwt_required
from app.domain.work_plans import (
    WorkPlanForbiddenError,
    WorkPlanNotFoundError,
    WorkPlanValidationError,
)
from app.routes.models.work_plan_models import (
    work_plan_all_response,
    work_plan_create_model,
    work_plan_edit_model,
    work_plan_filter_parser,
    work_plan_model,
    work_plan_msg_model,
    work_plan_response,
)
from app.schemas.work_plan_schemas import (
    WorkPlanCreateSchema,
    WorkPlanEditSchema,
    WorkPlanFilterSchema,
)
from app.use_cases.work_plans import (
    CreateWorkPlanCommand,
    CreateWorkPlanUseCase,
    DeleteWorkPlanUseCase,
    GetWorkPlanUseCase,
    ListWorkPlansUseCase,
    SoftDeleteWorkPlanUseCase,
    UpdateWorkPlanCommand,
    UpdateWorkPlanUseCase,
    WorkPlanActor,
    WorkPlanListQuery,
)
from app.web._typing import get_optional_uuid, to_plain_dict

work_plan_ns = Namespace("work_plans", description="Work plans management operations")
logger = logging.getLogger("ok_service")
for model in (
    work_plan_create_model,
    work_plan_edit_model,
    work_plan_model,
    work_plan_msg_model,
    work_plan_response,
    work_plan_all_response,
):
    work_plan_ns.models[model.name] = model


class CreatePayload(TypedDict):
    user_id: NotRequired[str | None]
    date: date
    summ: Any
    description: NotRequired[str | None]


class EditPayload(TypedDict, total=False):
    user_id: str | None
    date: date | None
    summ: Any
    description: str | None


class FilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
    year: int
    user_id: str
    user_id_is_null: bool
    deleted: bool


def _identity() -> dict[str, Any]:
    identity = (
        getattr(g, "api_key_identity_json", None)
        if getattr(g, "auth_via_api_key", False)
        else _get_jwt_identity()
    )
    if isinstance(identity, dict):
        return identity
    if isinstance(identity, (str, bytes, bytearray)):
        try:
            parsed = json.loads(identity)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError):
            return {}
    return {}


def _actor() -> WorkPlanActor:
    if getattr(g, "auth_via_api_key", False):
        return WorkPlanActor(role="admin")
    return WorkPlanActor(role=str(_identity().get("role") or "").strip().lower())


def _id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _map_error(error: Exception):
    if isinstance(error, WorkPlanNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, WorkPlanForbiddenError):
        return {"msg": str(error)}, 403
    if isinstance(error, (WorkPlanValidationError, ValidationError, ValueError)):
        return {"error": getattr(error, "messages", str(error))}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "A work plan already exists for this month and user."}, 409
    logger.exception("Unexpected work plan error")
    return {"msg": "Internal server error"}, 500


@work_plan_ns.route("/add")
class WorkPlanAdd(Resource):
    @api_key_or_jwt_required
    @admin_or_manager_required
    @work_plan_ns.expect(work_plan_create_model)
    @work_plan_ns.response(200, "Work plan created", work_plan_msg_model)
    def post(self):
        try:
            data = cast(
                CreatePayload,
                WorkPlanCreateSchema().load(
                    to_plain_dict(
                        request.get_json(silent=True), "Request body is required"
                    )
                ),
            )
            return {
                "msg": "Work plan added successfully",
                "work_plan_id": str(
                    CreateWorkPlanUseCase(SQLAlchemyWorkPlanRepository())
                    .execute(
                        CreateWorkPlanCommand(
                            user_id=get_optional_uuid(data, "user_id"),
                            date=data["date"],
                            summ=data["summ"],
                            description=data.get("description"),
                        ),
                        _actor(),
                    )
                    .work_plan_id
                ),
            }, 200
        except Exception as error:
            return _map_error(error)


@work_plan_ns.route("/<string:work_plan_id>/view")
class WorkPlanView(Resource):
    @api_key_or_jwt_required
    @admin_or_manager_required
    @work_plan_ns.response(200, "Work plan found", work_plan_response)
    def get(self, work_plan_id):
        try:
            item = GetWorkPlanUseCase(SQLAlchemyWorkPlanRepository()).execute(
                _id(work_plan_id)
            )
            return {
                "msg": "Work plan found successfully",
                "work_plan": work_plan_entity_to_response(item),
            }, 200
        except Exception as error:
            return _map_error(error)


@work_plan_ns.route("/<string:work_plan_id>/edit")
class WorkPlanEdit(Resource):
    @api_key_or_jwt_required
    @admin_or_manager_required
    @work_plan_ns.expect(work_plan_edit_model, validate=False)
    @work_plan_ns.response(200, "Work plan updated", work_plan_msg_model)
    def patch(self, work_plan_id):
        try:
            raw = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(EditPayload, WorkPlanEditSchema().load(raw))
            command = UpdateWorkPlanCommand(
                _id(work_plan_id),
                user_id=get_optional_uuid(data, "user_id"),
                user_id_is_set="user_id" in raw,
                date=data.get("date"),
                date_is_set="date" in raw,
                summ=data.get("summ"),
                summ_is_set="summ" in raw,
                description=data.get("description"),
                description_is_set="description" in raw,
            )
            item = UpdateWorkPlanUseCase(SQLAlchemyWorkPlanRepository()).execute(
                command, _actor()
            )
            return {
                "msg": "Work plan edited successfully",
                "work_plan_id": str(item.work_plan_id),
            }, 200
        except Exception as error:
            return _map_error(error)


@work_plan_ns.route("/<string:work_plan_id>/delete/soft")
class WorkPlanSoftDelete(Resource):
    @api_key_or_jwt_required
    @admin_or_manager_required
    @work_plan_ns.response(200, "Work plan soft deleted", work_plan_msg_model)
    def patch(self, work_plan_id):
        try:
            item = SoftDeleteWorkPlanUseCase(SQLAlchemyWorkPlanRepository()).execute(
                _id(work_plan_id), _actor()
            )
            return {
                "msg": f"Work plan {item.work_plan_id} soft deleted successfully",
                "work_plan_id": str(item.work_plan_id),
            }, 200
        except Exception as error:
            return _map_error(error)


@work_plan_ns.route("/<string:work_plan_id>/delete/hard")
class WorkPlanHardDelete(Resource):
    @api_key_or_jwt_required
    @admin_or_manager_required
    @work_plan_ns.response(200, "Work plan hard deleted", work_plan_msg_model)
    def delete(self, work_plan_id):
        try:
            DeleteWorkPlanUseCase(SQLAlchemyWorkPlanRepository()).execute(
                _id(work_plan_id), _actor()
            )
            return {
                "msg": f"Work plan {work_plan_id} hard deleted successfully",
                "work_plan_id": work_plan_id,
            }, 200
        except Exception as error:
            return _map_error(error)


@work_plan_ns.route("/all")
class WorkPlanAll(Resource):
    @api_key_or_jwt_required
    @admin_or_manager_required
    @work_plan_ns.expect(work_plan_filter_parser)
    @work_plan_ns.response(200, "Work plans found", work_plan_all_response)
    def get(self):
        try:
            raw = to_plain_dict(request.args, "Request query is required")
            data = cast(FilterPayload, WorkPlanFilterSchema().load(raw))
            user_id_value = data.get("user_id")
            item = ListWorkPlansUseCase(SQLAlchemyWorkPlanRepository()).execute(
                WorkPlanListQuery(
                    offset=data.get("offset", 0),
                    limit=data.get("limit", 1000),
                    sort_by=data.get("sort_by", "date"),
                    sort_order=data.get("sort_order", "asc"),
                    year=data.get("year"),
                    user_id=_id(user_id_value) if user_id_value else None,
                    user_id_is_null=data.get("user_id_is_null"),
                    deleted=data.get("deleted", False),
                )
            )
            return {
                "msg": "Work plans fetched successfully",
                "work_plans": [work_plan_entity_to_response(x) for x in item],
            }, 200
        except Exception as error:
            return _map_error(error)
