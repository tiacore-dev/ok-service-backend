# Namespace for ProjectSchedules
import json
import logging
from uuid import UUID

from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.decorators import user_forbidden
from app.routes.models.project_schedule_models import (
    project_schedule_all_response,
    project_schedule_create_model,
    project_schedule_filter_parser,
    project_schedule_model,
    project_schedule_msg_model,
    project_schedule_response,
)
from app.schemas.project_schedule_schemas import (
    ProjectScheduleCreateSchema,
    ProjectScheduleEditSchema,
    ProjectScheduleFilterSchema,
)

logger = logging.getLogger("ok_service")

project_schedule_ns = Namespace(
    "project_schedules", description="Project schedules management operations"
)

# Initialize models
project_schedule_ns.models[project_schedule_create_model.name] = (
    project_schedule_create_model
)
project_schedule_ns.models[project_schedule_msg_model.name] = project_schedule_msg_model
project_schedule_ns.models[project_schedule_response.name] = project_schedule_response
project_schedule_ns.models[project_schedule_all_response.name] = (
    project_schedule_all_response
)
project_schedule_ns.models[project_schedule_model.name] = project_schedule_model


@project_schedule_ns.route("/add")
class ProjectScheduleAdd(Resource):
    @jwt_required()
    @user_forbidden
    @project_schedule_ns.expect(project_schedule_create_model)
    @project_schedule_ns.marshal_with(project_schedule_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            "Request to add new project schedule", extra={"login": current_user}
        )

        schema = ProjectScheduleCreateSchema()
        try:
            data = schema.load(request.json)  # type: ignore
            logger.info(f"Полученные данные: {data}", extra={"login": current_user})
        except ValidationError as err:
            return {"error": err.messages}, 400

        try:
            from app.database.managers.projects_managers import (
                ProjectSchedulesManager,
                ProjectsManager,
            )

            db = ProjectSchedulesManager()
            db_p = ProjectsManager()

            if current_user["role"] == "project-leader":
                led_projects = db_p.get_all_filtered(
                    project_leader=current_user["user_id"]
                )
                logger.info(
                    f"Найденные projects: {led_projects}", extra={"login": current_user}
                )
                led_project_ids = {p["project_id"] for p in led_projects}
                if str(data["project"]) not in led_project_ids:  # type: ignore
                    logger.warning(
                        "Trying to add not own project schedule",
                        extra={"login": current_user},
                    )
                    return {"msg": "You cannot add not your projects"}, 403

            new_schedule = db.add(created_by=current_user["user_id"], **data)  # type: ignore
            logger.info(
                f"New project schedule added: {new_schedule['project_schedule_id']}",
                extra={"login": current_user},
            )
            return {
                "msg": "New project schedule added successfully",
                "project_schedule_id": new_schedule["project_schedule_id"],
            }, 200
        except Exception as e:
            logger.error(
                f"Error adding project schedule: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error adding project schedule: {e}"}, 500


@project_schedule_ns.route("/<string:schedule_id>/view")
class ProjectScheduleView(Resource):
    @jwt_required()
    @project_schedule_ns.marshal_with(project_schedule_response)
    def get(self, schedule_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to view project schedule: {schedule_id}",
            extra={"login": current_user},
        )
        try:
            schedule_id = UUID(schedule_id)
            from app.database.managers.projects_managers import ProjectSchedulesManager

            db = ProjectSchedulesManager()
            schedule = db.get_by_id(schedule_id)
            if not schedule:
                logger.warning(
                    f"Project schedule {schedule_id} not found",
                    extra={"login": current_user},
                )
                return {"msg": "Project schedule not found"}, 404
            return {
                "msg": "Project schedule found successfully",
                "project_schedule": schedule,
            }, 200
        except Exception as e:
            logger.error(
                f"Error viewing project schedule: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error viewing project schedule: {e}"}, 500


@project_schedule_ns.route("/<string:schedule_id>/delete/hard")
class ProjectScheduleHardDelete(Resource):
    @jwt_required()
    @user_forbidden
    @project_schedule_ns.marshal_with(project_schedule_msg_model)
    def delete(self, schedule_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to hard delete project schedule: {schedule_id}",
            extra={"login": current_user},
        )
        try:
            schedule_id = UUID(schedule_id)
            from app.database.managers.projects_managers import ProjectSchedulesManager

            db = ProjectSchedulesManager()

            if current_user["role"] == "project-leader":
                led_schedules = db.get_schedule_ids_by_project_leader(
                    current_user["user_id"]
                )
                if str(schedule_id) not in led_schedules:
                    logger.warning(
                        "Trying to hard delete not user's project schedule",
                        extra={"login": current_user},
                    )
                    return {"msg": "Forbidden"}, 403

            deleted = db.delete(record_id=schedule_id)
            if not deleted:
                logger.warning(
                    f"Project schedule {schedule_id} not found for hard delete",
                    extra={"login": current_user},
                )
                return {"msg": "Project schedule not found"}, 404
            return {
                "msg": f"Project schedule {schedule_id} hard deleted successfully",
                "project_schedule_id": schedule_id,
            }, 200
        except IntegrityError:
            logger.warning(
                f"Conflict on delete: dependent data exists for schedule {schedule_id}",
                extra={"login": current_user},
            )
            abort(
                409,
                description="Cannot delete project schedule: dependent data exists.",
            )
        except Exception as e:
            logger.error(
                f"Error hard deleting project schedule: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error hard deleting project schedule: {e}"}, 500


@project_schedule_ns.route("/<string:schedule_id>/edit")
class ProjectScheduleEdit(Resource):
    @jwt_required()
    @user_forbidden
    @project_schedule_ns.expect(project_schedule_create_model)
    @project_schedule_ns.marshal_with(project_schedule_msg_model)
    def patch(self, schedule_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to edit project schedule: {schedule_id}",
            extra={"login": current_user},
        )

        schema = ProjectScheduleEditSchema()
        try:
            data = schema.load(request.json)  # type: ignore
            logger.info(
                f"Validated data for edit: {data}", extra={"login": current_user}
            )
        except ValidationError as err:
            return {"error": err.messages}, 400

        try:
            schedule_id = UUID(schedule_id)
            from app.database.managers.projects_managers import ProjectSchedulesManager

            db = ProjectSchedulesManager()

            if current_user["role"] == "project-leader":
                led_schedules = db.get_schedule_ids_by_project_leader(
                    current_user["user_id"]
                )
                if str(schedule_id) not in led_schedules:
                    logger.warning(
                        "Trying to edit not user's project schedule",
                        extra={"login": current_user},
                    )
                    return {"msg": "Forbidden"}, 403

            updated = db.update(record_id=schedule_id, **data)  # type: ignore
            if not updated:
                logger.warning(
                    f"Project schedule {schedule_id} not found for edit",
                    extra={"login": current_user},
                )
                return {"msg": "Project schedule not found"}, 404
            return {
                "msg": "Project schedule updated successfully",
                "project_schedule_id": schedule_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error editing project schedule: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error editing project schedule: {e}"}, 500


@project_schedule_ns.route("/all")
class ProjectScheduleAll(Resource):
    @jwt_required()
    @project_schedule_ns.expect(project_schedule_filter_parser)
    @project_schedule_ns.marshal_with(project_schedule_all_response)
    def get(self):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            "Request to fetch all project schedules", extra={"login": current_user}
        )

        schema = ProjectScheduleFilterSchema()
        try:
            args = schema.load(request.args)
        except ValidationError as err:
            logger.error(
                f"Validation error: {err.messages}", extra={"login": current_user}
            )
            return {"error": err.messages}, 400

        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit", None)  # type: ignore
        sort_by = args.get("sort_by")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore
        filters = {
            "project": args.get("project"),  # type: ignore
            "work": args.get("work"),  # type: ignore
            "date": args.get("date"),  # type: ignore
            "created_by": args.get("created_by"),  # type: ignore
            "created_at": args.get("created_at"),  # type: ignore
        }

        logger.debug(
            f"Fetching project schedules with filters: {filters}, offset={
                offset
            }, limit={limit}",
            extra={"login": current_user},
        )

        try:
            from app.database.managers.projects_managers import ProjectSchedulesManager

            db = ProjectSchedulesManager()
            schedules = db.get_all_filtered(
                offset=offset,
                limit=limit,
                sort_by=sort_by,  # type: ignore
                sort_order=sort_order,
                **filters,
            )
            logger.info(
                f"Successfully fetched {len(schedules)} project schedules",
                extra={"login": current_user},
            )
            return {
                "msg": "Project schedules found successfully",
                "project_schedules": schedules,
            }, 200
        except Exception as e:
            logger.error(
                f"Error fetching project schedules: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error fetching project schedules: {e}"}, 500
