import json
import logging
from datetime import datetime
from uuid import UUID

from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.database.models.leaves import AbsenceReason
from app.decorators import admin_required
from app.routes.models.leave_models import (
    leave_all_response,
    leave_create_model,
    leave_edit_model,
    leave_filter_parser,
    leave_model,
    leave_msg_model,
    leave_reason_all_response,
    leave_reason_model,
    leave_response,
)
from app.schemas.leave_schemas import (
    LeaveCreateSchema,
    LeaveEditSchema,
    LeaveFilterSchema,
)

logger = logging.getLogger("ok_service")

leave_ns = Namespace("leaves", description="Leaves management operations")

leave_ns.models[leave_create_model.name] = leave_create_model
leave_ns.models[leave_msg_model.name] = leave_msg_model
leave_ns.models[leave_response.name] = leave_response
leave_ns.models[leave_all_response.name] = leave_all_response
leave_ns.models[leave_model.name] = leave_model
leave_ns.models[leave_edit_model.name] = leave_edit_model
leave_ns.models[leave_reason_model.name] = leave_reason_model
leave_ns.models[leave_reason_all_response.name] = leave_reason_all_response


def _current_timestamp():
    return int(datetime.utcnow().timestamp())


@leave_ns.route("/add")
class LeaveAdd(Resource):
    @jwt_required()
    @admin_required
    @leave_ns.expect(leave_edit_model)
    @leave_ns.marshal_with(leave_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to add new leave", extra={"login": current_user})

        schema = LeaveCreateSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while adding leave: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400

        from app.database.managers.leaves_manager import LeavesManager

        manager = LeavesManager()

        if manager.has_shift_conflict(
            data["user"],  # type: ignore
            data["start_date"],  # type: ignore
            data["end_date"],  # type: ignore
        ):
            logger.warning(
                "Shift exists within leave period",
                extra={"login": current_user},
            )
            return {"msg": "Shift exists within the specified period"}, 409

        if manager.has_overlapping_leave(
            data["user"],  # type: ignore
            data["start_date"],  # type: ignore
            data["end_date"],  # type: ignore
        ):
            logger.warning(
                "Leave overlaps with existing leave",
                extra={"login": current_user},
            )
            return {"msg": "Leave overlaps with existing record"}, 409

        try:
            new_leave = manager.add_leave(
                start_date=data["start_date"],  # type: ignore
                end_date=data["end_date"],  # type: ignore
                reason=data["reason"],  # type: ignore
                user_id=data["user"],  # type: ignore
                responsible_id=data["responsible"],  # type: ignore
                comment=data.get("comment"),  # type: ignore
                created_by=current_user["user_id"],  # type: ignore
            )
            logger.info(
                f"New leave added: {new_leave['leave_id']}",
                extra={"login": current_user},
            )
            return {
                "msg": "New leave added successfully",
                "leave_id": new_leave["leave_id"],
            }, 200
        except Exception as exc:
            logger.error(f"Error adding leave: {exc}", extra={"login": current_user})
            return {"msg": f"Error adding leave: {exc}"}, 500


@leave_ns.route("/<string:leave_id>/view")
class LeaveView(Resource):
    @jwt_required()
    @leave_ns.marshal_with(leave_response)
    def get(self, leave_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Request to view leave: {leave_id}", extra={"login": current_user})

        try:
            leave_uuid = UUID(leave_id)
        except ValueError as exc:
            raise ValueError("Invalid UUID format") from exc

        from app.database.managers.leaves_manager import LeavesManager

        manager = LeavesManager()
        leave = manager.get_by_id(leave_uuid)
        if not leave:
            return {"msg": "Leave not found"}, 404
        return {"msg": "Leave found successfully", "leave": leave}, 200


@leave_ns.route("/<string:leave_id>/delete/soft")
class LeaveSoftDelete(Resource):
    @jwt_required()
    @admin_required
    @leave_ns.marshal_with(leave_msg_model)
    def patch(self, leave_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to soft delete leave: {leave_id}", extra={"login": current_user}
        )

        try:
            leave_uuid = UUID(leave_id)
        except ValueError as exc:
            raise ValueError("Invalid UUID format") from exc

        from app.database.managers.leaves_manager import LeavesManager

        manager = LeavesManager()
        updated = manager.update_leave(
            leave_uuid,
            deleted=True,
            updated_by=current_user["user_id"],
            updated_at=_current_timestamp(),
        )
        if not updated:
            return {"msg": "Leave not found"}, 404
        return {
            "msg": f"Leave {leave_id} soft deleted successfully",
            "leave_id": leave_id,
        }, 200


@leave_ns.route("/<string:leave_id>/delete/hard")
class LeaveHardDelete(Resource):
    @jwt_required()
    @admin_required
    @leave_ns.marshal_with(leave_msg_model)
    def delete(self, leave_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to hard delete leave: {leave_id}", extra={"login": current_user}
        )

        try:
            leave_uuid = UUID(leave_id)
        except ValueError as exc:
            raise ValueError("Invalid UUID format") from exc

        from app.database.managers.leaves_manager import LeavesManager

        manager = LeavesManager()
        try:
            deleted = manager.delete(leave_uuid)
            if not deleted:
                return {"msg": "Leave not found"}, 404
            return {
                "msg": f"Leave {leave_id} hard deleted successfully",
                "leave_id": leave_id,
            }, 200
        except IntegrityError:
            abort(409, description="Cannot delete leave: dependent data exists.")
        except Exception as exc:
            logger.error(
                f"Error hard deleting leave: {exc}", extra={"login": current_user}
            )
            return {"msg": f"Error hard deleting leave: {exc}"}, 500


@leave_ns.route("/<string:leave_id>/edit")
class LeaveEdit(Resource):
    @jwt_required()
    @admin_required
    @leave_ns.expect(leave_create_model)
    @leave_ns.marshal_with(leave_msg_model)
    def patch(self, leave_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Request to edit leave: {leave_id}", extra={"login": current_user})

        schema = LeaveEditSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while editing leave: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400

        try:
            leave_uuid = UUID(leave_id)
        except ValueError as exc:
            raise ValueError("Invalid UUID format") from exc

        from app.database.managers.leaves_manager import LeavesManager

        manager = LeavesManager()
        existing_leave = manager.get_by_id(leave_uuid)
        if not existing_leave:
            return {"msg": "Leave not found"}, 404

        start_date = data.get("start_date", existing_leave["start_date"])  # type: ignore
        end_date = data.get("end_date", existing_leave["end_date"])  # type: ignore
        user_id = data.get("user", existing_leave["user"])  # type: ignore

        if manager.has_shift_conflict(user_id, start_date, end_date):
            logger.warning(
                "Shift exists within leave period (edit)",
                extra={"login": current_user},
            )
            return {"msg": "Shift exists within the specified period"}, 409

        if manager.has_overlapping_leave(
            user_id, start_date, end_date, exclude_id=leave_id
        ):
            logger.warning(
                "Leave overlaps with existing leave (edit)",
                extra={"login": current_user},
            )
            return {"msg": "Leave overlaps with existing record"}, 409

        update_payload = {
            "start_date": data.get("start_date"),  # type: ignore
            "end_date": data.get("end_date"),  # type: ignore
            "reason": data.get("reason"),  # type: ignore
            "user_id": data.get("user"),  # type: ignore
            "responsible_id": data.get("responsible"),  # type: ignore
            "comment": data.get("comment"),  # type: ignore
            "updated_by": current_user["user_id"],  # type: ignore
            "updated_at": _current_timestamp(),  # type: ignore
        }

        try:
            updated = manager.update_leave(leave_uuid, **update_payload)
            if not updated:
                return {"msg": "Leave not found"}, 404
            return {"msg": "Leave edited successfully", "leave_id": leave_id}, 200
        except Exception as exc:
            logger.error(f"Error editing leave: {exc}", extra={"login": current_user})
            return {"msg": f"Error editing leave: {exc}"}, 500


@leave_ns.route("/all")
class LeaveAll(Resource):
    @jwt_required()
    @leave_ns.expect(leave_filter_parser)
    @leave_ns.marshal_with(leave_all_response)
    def get(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to fetch all leaves", extra={"login": current_user})

        schema = LeaveFilterSchema()
        try:
            args = schema.load(request.args)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while filtering leaves: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400

        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit")  # type: ignore
        sort_by = args.get("sort_by", "created_at")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore

        filters = {
            "user": args.get("user"),  # type: ignore
            "responsible": args.get("responsible"),  # type: ignore
            "reason": args.get("reason"),  # type: ignore
            "date_from": args.get("date_from"),  # type: ignore
            "date_to": args.get("date_to"),  # type: ignore
            "deleted": args.get("deleted"),  # type: ignore
        }

        from app.database.managers.leaves_manager import LeavesManager

        manager = LeavesManager()
        leaves = manager.list_leaves(
            offset=offset,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            **filters,
        )
        return {"msg": "Leaves found successfully", "leaves": leaves}, 200


@leave_ns.route("/reasons/all")
class LeaveReasons(Resource):
    @jwt_required()
    @leave_ns.marshal_with(leave_reason_all_response)
    def get(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to fetch leave reasons", extra={"login": current_user})

        reasons = [
            {"reason_id": reason.value, "name": reason.label()}
            for reason in AbsenceReason
        ]

        return {"msg": "Leave reasons found successfully", "reasons": reasons}, 200
