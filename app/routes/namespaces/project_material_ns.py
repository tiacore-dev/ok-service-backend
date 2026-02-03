import json
import logging
from uuid import UUID

from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.decorators import admin_required
from app.routes.models.project_material_models import (
    project_material_all_response,
    project_material_create_model,
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


@project_material_ns.route("/add")
class ProjectMaterialAdd(Resource):
    @jwt_required()
    @admin_required
    @project_material_ns.expect(project_material_create_model)
    @project_material_ns.marshal_with(project_material_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            "Request to add new project material", extra={"login": current_user}
        )

        schema = ProjectMaterialCreateSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while adding project material: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        try:
            from app.database.managers.materials_manager import ProjectMaterialsManager

            db = ProjectMaterialsManager()
            new_record = db.add(created_by=current_user["user_id"], **data)  # type: ignore
            logger.info(
                f"New project material added: {new_record['project_material_id']}",
                extra={"login": current_user},
            )
            return {
                "msg": "Project material added successfully",
                "project_material_id": new_record["project_material_id"],
            }, 200
        except Exception as e:
            logger.error(
                f"Error adding project material: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error adding project material: {e}"}, 500


@project_material_ns.route("/<string:project_material_id>/view")
class ProjectMaterialView(Resource):
    @jwt_required()
    @project_material_ns.marshal_with(project_material_response)
    def get(self, project_material_id):
        current_user = get_jwt_identity()
        logger.info(
            f"Request to view project material: {project_material_id}",
            extra={"login": current_user},
        )
        try:
            try:
                project_material_id = UUID(project_material_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.materials_manager import ProjectMaterialsManager

            db = ProjectMaterialsManager()
            record = db.get_by_id(project_material_id)
            if not record:
                logger.warning(
                    f"Project material not found: {project_material_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Project material not found"}, 404
            return {
                "msg": "Project material found successfully",
                "project_material": record,
            }, 200
        except Exception as e:
            logger.error(
                f"Error viewing project material: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error viewing project material: {e}"}, 500


@project_material_ns.route("/<string:project_material_id>/delete/hard")
class ProjectMaterialHardDelete(Resource):
    @jwt_required()
    @admin_required
    @project_material_ns.marshal_with(project_material_msg_model)
    def delete(self, project_material_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to hard delete project material: {project_material_id}",
            extra={"login": current_user},
        )
        try:
            try:
                project_material_id = UUID(project_material_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.materials_manager import ProjectMaterialsManager

            db = ProjectMaterialsManager()
            deleted = db.delete(record_id=project_material_id)
            if not deleted:
                logger.warning(
                    f"Project material not found for hard delete: {
                        project_material_id
                    }",
                    extra={"login": current_user},
                )
                return {"msg": "Project material not found"}, 404
            return {
                "msg": f"Project material {
                    project_material_id
                } hard deleted successfully",
                "project_material_id": project_material_id,
            }, 200
        except IntegrityError:
            logger.warning(
                f"Cannot hard delete project material {
                    project_material_id
                } due to related data",
                extra={"login": current_user},
            )
            abort(
                409,
                description="Cannot delete project material: dependent data exists.",
            )
        except Exception as e:
            logger.error(
                f"Error hard deleting project material: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error hard deleting project material: {e}"}, 500


@project_material_ns.route("/<string:project_material_id>/edit")
class ProjectMaterialEdit(Resource):
    @jwt_required()
    @admin_required
    @project_material_ns.expect(project_material_create_model)
    @project_material_ns.marshal_with(project_material_msg_model)
    def patch(self, project_material_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to edit project material: {project_material_id}",
            extra={"login": current_user},
        )

        schema = ProjectMaterialEditSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while editing project material: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        try:
            try:
                project_material_id = UUID(project_material_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.materials_manager import ProjectMaterialsManager

            db = ProjectMaterialsManager()
            updated = db.update(record_id=project_material_id, **data)  # type: ignore
            if not updated:
                logger.warning(
                    f"Project material not found for edit: {project_material_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Project material not found"}, 404
            return {
                "msg": "Project material edited successfully",
                "project_material_id": project_material_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error editing project material: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error editing project material: {e}"}, 500


@project_material_ns.route("/all")
class ProjectMaterialAll(Resource):
    @jwt_required()
    @project_material_ns.expect(project_material_filter_parser)
    @project_material_ns.marshal_with(project_material_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info(
            "Request to fetch all project materials", extra={"login": current_user}
        )

        schema = ProjectMaterialFilterSchema()
        try:
            args = schema.load(request.args)
        except ValidationError as err:
            logger.error(
                f"Validation error while filtering project materials: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit", None)  # type: ignore
        sort_by = args.get("sort_by")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore
        filters = {
            "project": args.get("project"),  # type: ignore
            "material": args.get("material"),  # type: ignore
            "project_work": args.get("project_work"),  # type: ignore
            "created_by": args.get("created_by"),  # type: ignore
            "created_at": args.get("created_at"),  # type: ignore
        }

        logger.debug(
            f"Fetching project materials with filters: {filters}, offset={offset}, "
            f"limit={limit}, sort_by={sort_by}, sort_order={sort_order}",
            extra={"login": current_user},
        )

        try:
            from app.database.managers.materials_manager import ProjectMaterialsManager

            db = ProjectMaterialsManager()
            records = db.get_all_filtered(
                offset=offset,
                limit=limit,
                sort_by=sort_by,  # type: ignore
                sort_order=sort_order,
                **filters,
            )
            logger.info(
                f"Successfully fetched {len(records)} project materials",
                extra={"login": current_user},
            )
            return {
                "msg": "Project materials found successfully",
                "project_materials": records,
            }, 200
        except Exception as e:
            logger.error(
                f"Error fetching project materials: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error fetching project materials: {e}"}, 500
