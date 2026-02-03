import json
import logging
from uuid import UUID

from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.decorators import admin_required
from app.routes.models.shift_report_material_models import (
    shift_report_material_all_response,
    shift_report_material_create_model,
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

logger = logging.getLogger("ok_service")

shift_report_material_ns = Namespace(
    "shift_report_materials",
    description="Shift report materials management operations",
)

shift_report_material_ns.models[shift_report_material_create_model.name] = (
    shift_report_material_create_model
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


@shift_report_material_ns.route("/add")
class ShiftReportMaterialAdd(Resource):
    @jwt_required()
    @admin_required
    @shift_report_material_ns.expect(shift_report_material_create_model)
    @shift_report_material_ns.marshal_with(shift_report_material_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            "Request to add new shift report material", extra={"login": current_user}
        )

        schema = ShiftReportMaterialCreateSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while adding shift report material: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        try:
            from app.database.managers.materials_manager import (
                ShiftReportMaterialsManager,
            )

            db = ShiftReportMaterialsManager()
            new_record = db.add(created_by=current_user["user_id"], **data)  # type: ignore
            logger.info(
                f"New shift report material added: {
                    new_record['shift_report_material_id']
                }",
                extra={"login": current_user},
            )
            return {
                "msg": "Shift report material added successfully",
                "shift_report_material_id": new_record["shift_report_material_id"],
            }, 200
        except Exception as e:
            logger.error(
                f"Error adding shift report material: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error adding shift report material: {e}"}, 500


@shift_report_material_ns.route("/<string:shift_report_material_id>/view")
class ShiftReportMaterialView(Resource):
    @jwt_required()
    @shift_report_material_ns.marshal_with(shift_report_material_response)
    def get(self, shift_report_material_id):
        current_user = get_jwt_identity()
        logger.info(
            f"Request to view shift report material: {shift_report_material_id}",
            extra={"login": current_user},
        )
        try:
            try:
                shift_report_material_id = UUID(shift_report_material_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.materials_manager import (
                ShiftReportMaterialsManager,
            )

            db = ShiftReportMaterialsManager()
            record = db.get_by_id(shift_report_material_id)
            if not record:
                logger.warning(
                    f"Shift report material not found: {shift_report_material_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Shift report material not found"}, 404
            return {
                "msg": "Shift report material found successfully",
                "shift_report_material": record,
            }, 200
        except Exception as e:
            logger.error(
                f"Error viewing shift report material: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error viewing shift report material: {e}"}, 500


@shift_report_material_ns.route("/<string:shift_report_material_id>/delete/hard")
class ShiftReportMaterialHardDelete(Resource):
    @jwt_required()
    @admin_required
    @shift_report_material_ns.marshal_with(shift_report_material_msg_model)
    def delete(self, shift_report_material_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to hard delete shift report material: {shift_report_material_id}",
            extra={"login": current_user},
        )
        try:
            try:
                shift_report_material_id = UUID(shift_report_material_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.materials_manager import (
                ShiftReportMaterialsManager,
            )

            db = ShiftReportMaterialsManager()
            deleted = db.delete(record_id=shift_report_material_id)
            if not deleted:
                logger.warning(
                    f"Shift report material not found for hard delete: {
                        shift_report_material_id
                    }",
                    extra={"login": current_user},
                )
                return {"msg": "Shift report material not found"}, 404
            return {
                "msg": f"Shift report material {
                    shift_report_material_id
                } hard deleted successfully",
                "shift_report_material_id": shift_report_material_id,
            }, 200
        except IntegrityError:
            logger.warning(
                f"Cannot hard delete shift report material {
                    shift_report_material_id
                } due to related data",
                extra={"login": current_user},
            )
            abort(
                409,
                description="Cannot delete shift report "
                "material: dependent data exists.",
            )
        except Exception as e:
            logger.error(
                f"Error hard deleting shift report material: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error hard deleting shift report material: {e}"}, 500


@shift_report_material_ns.route("/<string:shift_report_material_id>/edit")
class ShiftReportMaterialEdit(Resource):
    @jwt_required()
    @admin_required
    @shift_report_material_ns.expect(shift_report_material_create_model)
    @shift_report_material_ns.marshal_with(shift_report_material_msg_model)
    def patch(self, shift_report_material_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to edit shift report material: {shift_report_material_id}",
            extra={"login": current_user},
        )

        schema = ShiftReportMaterialEditSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while editing shift report material: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        try:
            try:
                shift_report_material_id = UUID(shift_report_material_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.materials_manager import (
                ShiftReportMaterialsManager,
            )

            db = ShiftReportMaterialsManager()
            updated = db.update(record_id=shift_report_material_id, **data)  # type: ignore
            if not updated:
                logger.warning(
                    f"Shift report material not found for edit: {
                        shift_report_material_id
                    }",
                    extra={"login": current_user},
                )
                return {"msg": "Shift report material not found"}, 404
            return {
                "msg": "Shift report material edited successfully",
                "shift_report_material_id": shift_report_material_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error editing shift report material: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error editing shift report material: {e}"}, 500


@shift_report_material_ns.route("/all")
class ShiftReportMaterialAll(Resource):
    @jwt_required()
    @shift_report_material_ns.expect(shift_report_material_filter_parser)
    @shift_report_material_ns.marshal_with(shift_report_material_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info(
            "Request to fetch all shift report materials", extra={"login": current_user}
        )

        schema = ShiftReportMaterialFilterSchema()
        try:
            args = schema.load(request.args)
        except ValidationError as err:
            logger.error(
                f"Validation error while filtering shift report materials: {
                    err.messages
                }",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit", None)  # type: ignore
        sort_by = args.get("sort_by")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore
        filters = {
            "shift_report": args.get("shift_report"),  # type: ignore
            "material": args.get("material"),  # type: ignore
            "shift_report_detail": args.get("shift_report_detail"),  # type: ignore
            "created_by": args.get("created_by"),  # type: ignore
            "created_at": args.get("created_at"),  # type: ignore
        }

        logger.debug(
            f"Fetching shift report materials with filters: {filters}, offset={
                offset
            }, "
            f"limit={limit}, sort_by={sort_by}, sort_order={sort_order}",
            extra={"login": current_user},
        )

        try:
            from app.database.managers.materials_manager import (
                ShiftReportMaterialsManager,
            )

            db = ShiftReportMaterialsManager()
            records = db.get_all_filtered(
                offset=offset,
                limit=limit,
                sort_by=sort_by,  # type: ignore
                sort_order=sort_order,
                **filters,
            )
            logger.info(
                f"Successfully fetched {len(records)} shift report materials",
                extra={"login": current_user},
            )
            return {
                "msg": "Shift report materials found successfully",
                "shift_report_materials": records,
            }, 200
        except Exception as e:
            logger.error(
                f"Error fetching shift report materials: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error fetching shift report materials: {e}"}, 500
