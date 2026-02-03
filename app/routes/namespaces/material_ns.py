import json
import logging
from uuid import UUID

from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.decorators import admin_required
from app.routes.models.material_models import (
    material_all_response,
    material_create_model,
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

logger = logging.getLogger("ok_service")

material_ns = Namespace("materials", description="Materials management operations")

material_ns.models[material_create_model.name] = material_create_model
material_ns.models[material_msg_model.name] = material_msg_model
material_ns.models[material_response.name] = material_response
material_ns.models[material_all_response.name] = material_all_response
material_ns.models[material_model.name] = material_model


@material_ns.route("/add")
class MaterialAdd(Resource):
    @jwt_required()
    @admin_required
    @material_ns.expect(material_create_model)
    @material_ns.marshal_with(material_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to add new material", extra={"login": current_user})

        schema = MaterialCreateSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while adding material: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        try:
            from app.database.managers.materials_manager import MaterialsManager

            db = MaterialsManager()
            new_material = db.add(created_by=current_user["user_id"], **data)  # type: ignore
            logger.info(
                f"New material added: {new_material['material_id']}",
                extra={"login": current_user},
            )
            return {
                "msg": "New material added successfully",
                "material_id": new_material["material_id"],
            }, 200
        except Exception as e:
            logger.error(f"Error adding material: {e}", extra={"login": current_user})
            return {"msg": f"Error adding material: {e}"}, 500


@material_ns.route("/<string:material_id>/view")
class MaterialView(Resource):
    @jwt_required()
    @material_ns.marshal_with(material_response)
    def get(self, material_id):
        current_user = get_jwt_identity()
        logger.info(
            f"Request to view material: {material_id}", extra={"login": current_user}
        )
        try:
            try:
                material_id = UUID(material_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.materials_manager import MaterialsManager

            db = MaterialsManager()
            material = db.get_by_id(material_id)
            if not material:
                logger.warning(
                    f"Material not found: {material_id}", extra={"login": current_user}
                )
                return {"msg": "Material not found"}, 404
            return {"msg": "Material found successfully", "material": material}, 200
        except Exception as e:
            logger.error(f"Error viewing material: {e}", extra={"login": current_user})
            return {"msg": f"Error viewing material: {e}"}, 500


@material_ns.route("/<string:material_id>/delete/soft")
class MaterialSoftDelete(Resource):
    @jwt_required()
    @admin_required
    @material_ns.marshal_with(material_msg_model)
    def patch(self, material_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to soft delete material: {material_id}",
            extra={"login": current_user},
        )
        try:
            try:
                material_id = UUID(material_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.materials_manager import MaterialsManager

            db = MaterialsManager()
            updated = db.update(record_id=material_id, deleted=True)
            if not updated:
                logger.warning(
                    f"Material not found for soft delete: {material_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Material not found"}, 404
            return {
                "msg": f"Material {material_id} soft deleted successfully",
                "material_id": material_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error soft deleting material: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error soft deleting material: {e}"}, 500


@material_ns.route("/<string:material_id>/delete/hard")
class MaterialHardDelete(Resource):
    @jwt_required()
    @admin_required
    @material_ns.marshal_with(material_msg_model)
    def delete(self, material_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to hard delete material: {material_id}",
            extra={"login": current_user},
        )
        try:
            try:
                material_id = UUID(material_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.materials_manager import MaterialsManager

            db = MaterialsManager()
            deleted = db.delete(record_id=material_id)
            if not deleted:
                logger.warning(
                    f"Material not found for hard delete: {material_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Material not found"}, 404
            return {
                "msg": f"Material {material_id} hard deleted successfully",
                "material_id": material_id,
            }, 200
        except IntegrityError:
            logger.warning(
                f"Cannot hard delete material {material_id} due to related data",
                extra={"login": current_user},
            )
            abort(409, description="Cannot delete material: dependent data exists.")
        except Exception as e:
            logger.error(
                f"Error hard deleting material: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error hard deleting material: {e}"}, 500


@material_ns.route("/<string:material_id>/edit")
class MaterialEdit(Resource):
    @jwt_required()
    @admin_required
    @material_ns.expect(material_create_model)
    @material_ns.marshal_with(material_msg_model)
    def patch(self, material_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to edit material: {material_id}", extra={"login": current_user}
        )

        schema = MaterialEditSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while editing material: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        try:
            try:
                material_id = UUID(material_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.materials_manager import MaterialsManager

            db = MaterialsManager()
            updated = db.update(record_id=material_id, **data)  # type: ignore
            if not updated:
                logger.warning(
                    f"Material not found for edit: {material_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Material not found"}, 404
            return {
                "msg": "Material edited successfully",
                "material_id": material_id,
            }, 200
        except Exception as e:
            logger.error(f"Error editing material: {e}", extra={"login": current_user})
            return {"msg": f"Error editing material: {e}"}, 500


@material_ns.route("/all")
class MaterialAll(Resource):
    @jwt_required()
    @material_ns.expect(material_filter_parser)
    @material_ns.marshal_with(material_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info("Request to fetch all materials", extra={"login": current_user})

        schema = MaterialFilterSchema()
        try:
            args = schema.load(request.args)
        except ValidationError as err:
            logger.error(
                f"Validation error while filtering materials: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit", None)  # type: ignore
        sort_by = args.get("sort_by")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore
        filters = {
            "name": args.get("name"),  # type: ignore
            "measurement_unit": args.get("measurement_unit"),  # type: ignore
            "deleted": args.get("deleted"),  # type: ignore
            "created_by": args.get("created_by"),  # type: ignore
            "created_at": args.get("created_at"),  # type: ignore
        }

        logger.debug(
            f"Fetching materials with filters: {filters}, offset={offset}, limit={
                limit
            }, "
            f"sort_by={sort_by}, sort_order={sort_order}",
            extra={"login": current_user},
        )

        try:
            from app.database.managers.materials_manager import MaterialsManager

            db = MaterialsManager()
            materials = db.get_all_filtered(
                offset=offset,
                limit=limit,
                sort_by=sort_by,  # type: ignore
                sort_order=sort_order,
                **filters,
            )
            logger.info(
                f"Successfully fetched {len(materials)} materials",
                extra={"login": current_user},
            )
            return {"msg": "Materials found successfully", "materials": materials}, 200
        except Exception as e:
            logger.error(
                f"Error fetching materials: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error fetching materials: {e}"}, 500
