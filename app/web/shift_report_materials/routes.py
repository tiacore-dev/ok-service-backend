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

from app.adapters.shift_report_materials import (
    SQLAlchemyShiftReportMaterialRepository,
    shift_report_material_entity_to_response,
)
from app.database.managers.shift_reports_managers import ShiftReportsManager
from app.decorators import api_key_or_jwt_required
from app.domain.shift_report_materials import (
    ShiftReportMaterialNotFoundError,
    ShiftReportMaterialValidationError,
)
from app.routes.models.shift_report_material_models import (
    shift_report_material_all_response,
    shift_report_material_create_model,
    shift_report_material_edit_model,
    shift_report_material_filter_parser,
    shift_report_material_model,
    shift_report_material_msg_model,
    shift_report_material_response,
)
from app.schemas.shift_report_material_schemas import (
    ShiftReportMaterialCreateSchema,
    ShiftReportMaterialEditSchema,
    ShiftReportMaterialFilterSchema,
)
from app.use_cases.shift_report_materials import (
    CreateShiftReportMaterialCommand,
    CreateShiftReportMaterialUseCase,
    DeleteShiftReportMaterialUseCase,
    GetShiftReportMaterialUseCase,
    ListShiftReportMaterialsUseCase,
    ShiftReportMaterialListQuery,
    UpdateShiftReportMaterialCommand,
    UpdateShiftReportMaterialUseCase,
)
from app.web._typing import (
    get_optional_decimal,
    get_optional_int,
    get_optional_str,
    get_optional_uuid,
    get_required_decimal,
    get_required_uuid,
    to_plain_dict,
)

logger = logging.getLogger("ok_service")

shift_report_material_ns = Namespace(
    "shift_report_materials",
    description="Shift report materials management operations",
)

shift_report_material_ns.models[shift_report_material_create_model.name] = (
    shift_report_material_create_model
)
shift_report_material_ns.models[shift_report_material_edit_model.name] = (
    shift_report_material_edit_model
)
shift_report_material_ns.models[shift_report_material_msg_model.name] = (
    shift_report_material_msg_model
)
shift_report_material_ns.models[shift_report_material_response.name] = (
    shift_report_material_response
)
shift_report_material_ns.models[shift_report_material_all_response.name] = (
    shift_report_material_all_response
)
shift_report_material_ns.models[shift_report_material_model.name] = (
    shift_report_material_model
)


class ShiftReportMaterialCreatePayload(TypedDict):
    shift_report: str
    material: str
    quantity: float | int
    shift_report_detail: NotRequired[str | None]


class ShiftReportMaterialEditPayload(TypedDict, total=False):
    shift_report: str
    material: str
    quantity: float | int
    shift_report_detail: NotRequired[str | None]


class ShiftReportMaterialFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    sort_by: str
    sort_order: str
    shift_report: str
    material: str
    shift_report_detail: str
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


def _repository() -> SQLAlchemyShiftReportMaterialRepository:
    return SQLAlchemyShiftReportMaterialRepository()


def _parse_shift_report_material_id(shift_report_material_id: str) -> UUID:
    try:
        return UUID(shift_report_material_id)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _check_shift_report_access(current_user: dict[str, Any], shift_report_id: str):
    if current_user.get("role") == "admin":
        return None

    try:
        parsed_shift_report_id = UUID(shift_report_id)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc

    shift_reports_manager = ShiftReportsManager()
    shift_report = shift_reports_manager.get_by_id(record_id=parsed_shift_report_id)
    if not shift_report:
        return {"msg": "Shift report not found"}, 404
    if shift_report["user"] != current_user.get("user_id") or shift_report["signed"] is True:
        return {"msg": "Forbidden"}, 403
    return None


def _map_error(error: Exception):
    if isinstance(error, ShiftReportMaterialNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, ShiftReportMaterialValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {
            "msg": "Cannot delete shift report material: dependent data exists."
        }, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@shift_report_material_ns.route("/add")
class ShiftReportMaterialAdd(Resource):
    @api_key_or_jwt_required
    @shift_report_material_ns.expect(shift_report_material_create_model, validate=False)
    @shift_report_material_ns.marshal_with(shift_report_material_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info(
            "Request to add new shift report material", extra={"login": current_user}
        )

        schema = ShiftReportMaterialCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(ShiftReportMaterialCreatePayload, schema.load(raw_payload))
            shift_report_id = get_required_uuid(
                data, "shift_report", "Shift report is required"
            )
            access_error = _check_shift_report_access(
                current_user, str(shift_report_id)
            )
            if access_error:
                return access_error
            record = CreateShiftReportMaterialUseCase(repository=_repository()).execute(
                CreateShiftReportMaterialCommand(
                    shift_report=shift_report_id,
                    material=get_required_uuid(data, "material", "Material is required"),
                    quantity=get_required_decimal(
                        data, "quantity", "Quantity is required"
                    ),
                    shift_report_detail=get_optional_uuid(data, "shift_report_detail"),
                    created_by=get_required_uuid(
                        current_user, "user_id", "Current user id is required"
                    ),
                )
            )
            return {
                "msg": "Shift report material added successfully",
                "shift_report_material_id": str(record.shift_report_material_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error adding shift report material: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@shift_report_material_ns.route("/<string:shift_report_material_id>/view")
class ShiftReportMaterialView(Resource):
    @api_key_or_jwt_required
    @shift_report_material_ns.marshal_with(shift_report_material_response)
    def get(self, shift_report_material_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to view shift report material: {shift_report_material_id}",
            extra={"login": current_user},
        )
        try:
            record = GetShiftReportMaterialUseCase(repository=_repository()).execute(
                _parse_shift_report_material_id(shift_report_material_id)
            )
            return {
                "msg": "Shift report material found successfully",
                "shift_report_material": shift_report_material_entity_to_response(
                    record
                ),
            }, 200
        except Exception as error:
            logger.error(
                f"Error viewing shift report material: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@shift_report_material_ns.route("/<string:shift_report_material_id>/delete/hard")
class ShiftReportMaterialHardDelete(Resource):
    @api_key_or_jwt_required
    @shift_report_material_ns.marshal_with(shift_report_material_msg_model)
    def delete(self, shift_report_material_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete shift report material: {shift_report_material_id}",
            extra={"login": current_user},
        )
        try:
            existing = GetShiftReportMaterialUseCase(repository=_repository()).execute(
                _parse_shift_report_material_id(shift_report_material_id)
            )
            access_error = _check_shift_report_access(
                current_user, str(existing.shift_report)
            )
            if access_error:
                return access_error
            deleted = DeleteShiftReportMaterialUseCase(repository=_repository()).execute(
                _parse_shift_report_material_id(shift_report_material_id)
            )
            if not deleted:
                raise ShiftReportMaterialNotFoundError(
                    "Shift report material not found"
                )
            return {
                "msg": f"Shift report material {shift_report_material_id} hard deleted successfully",
                "shift_report_material_id": shift_report_material_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error hard deleting shift report material: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@shift_report_material_ns.route("/<string:shift_report_material_id>/edit")
class ShiftReportMaterialEdit(Resource):
    @api_key_or_jwt_required
    @shift_report_material_ns.expect(shift_report_material_edit_model, validate=False)
    @shift_report_material_ns.marshal_with(shift_report_material_msg_model)
    def patch(self, shift_report_material_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to edit shift report material: {shift_report_material_id}",
            extra={"login": current_user},
        )

        schema = ShiftReportMaterialEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(ShiftReportMaterialEditPayload, schema.load(raw_payload))
            current = GetShiftReportMaterialUseCase(repository=_repository()).execute(
                _parse_shift_report_material_id(shift_report_material_id)
            )
            target_shift_report = get_optional_uuid(data, "shift_report")
            access_error = _check_shift_report_access(
                current_user,
                str(target_shift_report if target_shift_report is not None else current.shift_report),
            )
            if access_error:
                return access_error
            record = UpdateShiftReportMaterialUseCase(repository=_repository()).execute(
                UpdateShiftReportMaterialCommand(
                    shift_report_material_id=_parse_shift_report_material_id(
                        shift_report_material_id
                    ),
                    shift_report=target_shift_report,
                    material=get_optional_uuid(data, "material"),
                    quantity=get_optional_decimal(data, "quantity"),
                    shift_report_detail=get_optional_uuid(data, "shift_report_detail"),
                )
            )
            return {
                "msg": "Shift report material edited successfully",
                "shift_report_material_id": str(record.shift_report_material_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error editing shift report material: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@shift_report_material_ns.route("/all")
class ShiftReportMaterialAll(Resource):
    @api_key_or_jwt_required
    @shift_report_material_ns.expect(shift_report_material_filter_parser)
    @shift_report_material_ns.marshal_with(shift_report_material_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info(
            "Request to fetch all shift report materials", extra={"login": current_user}
        )

        schema = ShiftReportMaterialFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            args = cast(ShiftReportMaterialFilterPayload, schema.load(raw_args))
            query = ShiftReportMaterialListQuery(
                offset=get_optional_int(args, "offset") or 0,
                limit=get_optional_int(args, "limit"),
                sort_by=get_optional_str(args, "sort_by") or "created_at",
                sort_order=get_optional_str(args, "sort_order") or "desc",
                shift_report=get_optional_uuid(args, "shift_report"),
                material=get_optional_uuid(args, "material"),
                shift_report_detail=get_optional_uuid(args, "shift_report_detail"),
                created_by=get_optional_uuid(args, "created_by"),
                created_at=get_optional_int(args, "created_at"),
            )
            records = ListShiftReportMaterialsUseCase(repository=_repository()).execute(
                query
            )
            return {
                "msg": "Shift report materials found successfully",
                "shift_report_materials": [
                    shift_report_material_entity_to_response(item) for item in records
                ],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching shift report materials: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)
