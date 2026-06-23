from __future__ import annotations

import json
import logging
from decimal import Decimal
from typing import Any, TypedDict, cast
from uuid import UUID

from flask import g, request
from flask_jwt_extended import get_jwt_identity as _get_jwt_identity
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.adapters.work_prices import (
    SQLAlchemyWorkPriceRepository,
    work_price_entity_to_response,
)
from app.decorators import admin_required, api_key_or_jwt_required
from app.domain.work_prices import WorkPriceNotFoundError, WorkPriceValidationError
from app.routes.models.work_price_models import (
    work_price_all_response,
    work_price_create_model,
    work_price_edit_model,
    work_price_filter_parser,
    work_price_model,
    work_price_msg_model,
    work_price_response,
)
from app.schemas.work_price_schemas import (
    WorkPriceCreateSchema,
    WorkPriceEditSchema,
    WorkPriceFilterSchema,
)
from app.use_cases.work_prices import (
    CreateWorkPriceCommand,
    CreateWorkPriceUseCase,
    DeleteWorkPriceUseCase,
    GetWorkPriceUseCase,
    ListWorkPricesUseCase,
    UpdateWorkPriceCommand,
    UpdateWorkPriceUseCase,
    WorkPriceListQuery,
)
from app.web._typing import (
    get_optional_bool,
    get_optional_int,
    get_optional_str,
    optional_uuid,
    required_uuid,
    to_plain_dict,
)

logger = logging.getLogger("ok_service")

work_price_ns = Namespace(
    "work_prices", description="Work Prices management operations"
)

work_price_ns.models[work_price_create_model.name] = work_price_create_model
work_price_ns.models[work_price_msg_model.name] = work_price_msg_model
work_price_ns.models[work_price_response.name] = work_price_response
work_price_ns.models[work_price_all_response.name] = work_price_all_response
work_price_ns.models[work_price_model.name] = work_price_model


class WorkPriceCreatePayload(TypedDict):
    work: str
    category: int
    price: Decimal | float | int


class WorkPriceEditPayload(TypedDict, total=False):
    work: str
    category: int
    price: Decimal | float | int
    deleted: bool


class WorkPriceFilterPayload(TypedDict, total=False):
    offset: int
    limit: int
    work: str
    category: int
    price: Decimal | float | int
    created_by: str
    created_at: int
    deleted: bool
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


def _repository() -> SQLAlchemyWorkPriceRepository:
    return SQLAlchemyWorkPriceRepository()


def _parse_work_price_id(work_price_id: str) -> UUID:
    try:
        return UUID(work_price_id)
    except ValueError as exc:
        raise ValueError("Invalid UUID format") from exc


def _map_error(error: Exception):
    if isinstance(error, WorkPriceNotFoundError):
        return {"msg": str(error)}, 404
    if isinstance(error, WorkPriceValidationError):
        return {"msg": str(error)}, 400
    if isinstance(error, IntegrityError):
        return {"msg": "Cannot delete work price: dependent data exists."}, 409
    if isinstance(error, ValidationError):
        return {"error": error.messages}, 400
    if isinstance(error, ValueError):
        return {"msg": str(error)}, 400
    return {"msg": f"Internal error: {error}"}, 500


@work_price_ns.route("/add")
class WorkPriceAdd(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_price_ns.expect(work_price_create_model)
    @work_price_ns.marshal_with(work_price_msg_model)
    def post(self):
        current_user = _get_current_user()
        logger.info("Request to add new work price", extra={"login": current_user})

        schema = WorkPriceCreateSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(WorkPriceCreatePayload, schema.load(raw_payload))
            command = CreateWorkPriceCommand(
                work=required_uuid(data["work"], "Work is required"),
                category=int(data["category"]),
                price=Decimal(str(data["price"])),
                created_by=required_uuid(
                    get_optional_str(current_user, "user_id"),
                    "Current user id is required",
                ),
            )
            work_price = CreateWorkPriceUseCase(repository=_repository()).execute(
                command
            )
            return {
                "msg": "New work price added successfully",
                "work_price_id": str(work_price.work_price_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error adding work price: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@work_price_ns.route("/<string:work_price_id>/view")
class WorkPriceView(Resource):
    @api_key_or_jwt_required
    @work_price_ns.marshal_with(work_price_response)
    def get(self, work_price_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to view work price: {work_price_id}",
            extra={"login": current_user},
        )
        try:
            work_price = GetWorkPriceUseCase(repository=_repository()).execute(
                _parse_work_price_id(work_price_id)
            )
            return {
                "msg": "Work price found successfully",
                "work_price": work_price_entity_to_response(work_price),
            }, 200
        except Exception as error:
            logger.error(
                f"Error viewing work price: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@work_price_ns.route("/<string:work_price_id>/delete/soft")
class WorkPriceSoftDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_price_ns.marshal_with(work_price_msg_model)
    def patch(self, work_price_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to soft delete work price: {work_price_id}",
            extra={"login": current_user},
        )
        try:
            work_price = UpdateWorkPriceUseCase(repository=_repository()).execute(
                UpdateWorkPriceCommand(
                    work_price_id=_parse_work_price_id(work_price_id),
                    deleted=True,
                )
            )
            return {
                "msg": f"Work price {
                    work_price.work_price_id
                } soft deleted successfully",
                "work_price_id": str(work_price.work_price_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error soft deleting work price: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@work_price_ns.route("/<string:work_price_id>/delete/hard")
class WorkPriceHardDelete(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_price_ns.marshal_with(work_price_msg_model)
    def delete(self, work_price_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to hard delete work price: {work_price_id}",
            extra={"login": current_user},
        )
        try:
            deleted = DeleteWorkPriceUseCase(repository=_repository()).execute(
                _parse_work_price_id(work_price_id)
            )
            if not deleted:
                raise WorkPriceNotFoundError("Work price not found")
            return {
                "msg": f"Work price {work_price_id} hard deleted successfully",
                "work_price_id": work_price_id,
            }, 200
        except Exception as error:
            logger.error(
                f"Error hard deleting work price: {error}",
                extra={"login": current_user},
            )
            return _map_error(error)


@work_price_ns.route("/<string:work_price_id>/edit")
class WorkPriceEdit(Resource):
    @api_key_or_jwt_required
    @admin_required
    @work_price_ns.expect(work_price_edit_model)
    @work_price_ns.marshal_with(work_price_msg_model)
    def patch(self, work_price_id):
        current_user = _get_current_user()
        logger.info(
            f"Request to edit work price: {work_price_id}",
            extra={"login": current_user},
        )

        schema = WorkPriceEditSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(WorkPriceEditPayload, schema.load(raw_payload))
            price_value = data.get("price")
            work_price = UpdateWorkPriceUseCase(repository=_repository()).execute(
                UpdateWorkPriceCommand(
                    work_price_id=_parse_work_price_id(work_price_id),
                    work=optional_uuid(data.get("work")),
                    category=get_optional_int(data, "category"),
                    price=Decimal(str(price_value))
                    if price_value is not None
                    else None,
                    deleted=get_optional_bool(data, "deleted"),
                )
            )
            return {
                "msg": "Work price edited successfully",
                "work_price_id": str(work_price.work_price_id),
            }, 200
        except Exception as error:
            logger.error(
                f"Error editing work price: {error}", extra={"login": current_user}
            )
            return _map_error(error)


@work_price_ns.route("/all")
class WorkPriceAll(Resource):
    @api_key_or_jwt_required
    @work_price_ns.expect(work_price_filter_parser)
    @work_price_ns.marshal_with(work_price_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all work prices", extra={"login": current_user})

        schema = WorkPriceFilterSchema()
        try:
            raw_args = to_plain_dict(request.args, "Request query is required")
            args = cast(WorkPriceFilterPayload, schema.load(raw_args))
            price_value = args.get("price")
            query = WorkPriceListQuery(
                offset=get_optional_int(args, "offset") or 0,
                limit=get_optional_int(args, "limit"),
                sort_by=get_optional_str(args, "sort_by") or "created_at",
                sort_order=get_optional_str(args, "sort_order") or "desc",
                work=optional_uuid(args.get("work")),
                category=get_optional_int(args, "category"),
                price=Decimal(str(price_value)) if price_value is not None else None,
                created_by=optional_uuid(args.get("created_by")),
                created_at=get_optional_int(args, "created_at"),
                deleted=get_optional_bool(args, "deleted"),
            )
            work_prices = ListWorkPricesUseCase(repository=_repository()).execute(query)
            return {
                "msg": "Work prices found successfully",
                "work_prices": [
                    work_price_entity_to_response(item) for item in work_prices
                ],
            }, 200
        except Exception as error:
            logger.error(
                f"Error fetching work prices: {error}", extra={"login": current_user}
            )
            return _map_error(error)
