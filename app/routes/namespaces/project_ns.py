import json
import logging
from uuid import UUID

from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.decorators import user_forbidden
from app.routes.models.project_models import (
    project_all_response,
    project_create_model,
    project_filter_parser,
    project_model,
    project_msg_model,
    project_response,
    project_stats_model,
    project_stats_response,
)
from app.schemas.project_schemas import (
    ProjectCreateSchema,
    ProjectEditSchema,
    ProjectFilterSchema,
)

logger = logging.getLogger("ok_service")

project_ns = Namespace("projects", description="Projects management operations")

# Инициализация моделей
project_ns.models[project_create_model.name] = project_create_model
project_ns.models[project_msg_model.name] = project_msg_model
project_ns.models[project_response.name] = project_response
project_ns.models[project_all_response.name] = project_all_response
project_ns.models[project_model.name] = project_model
project_ns.models[project_stats_model.name] = project_stats_model
project_ns.models[project_stats_response.name] = project_stats_response


@project_ns.route("/add")
class ProjectAdd(Resource):
    @jwt_required()
    @user_forbidden
    @project_ns.expect(project_create_model)
    @project_ns.marshal_with(project_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to add new project", extra={"login": current_user})

        schema = ProjectCreateSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            return {"error": err.messages}, 400
        try:
            from app.database.managers.projects_managers import ProjectsManager

            db = ProjectsManager()
            if current_user["role"] == "project-leader":
                data["project_leader"] = current_user["user_id"]  # type: ignore
            new_project = db.add(created_by=current_user["user_id"], **data)  # type: ignore
            logger.info(
                f"New project added: {new_project['project_id']}",
                extra={"login": current_user},
            )
            return {
                "msg": "New project added successfully",
                "project_id": new_project["project_id"],
            }, 200
        except Exception as e:
            logger.error(f"Error adding project: {e}", extra={"login": current_user})
            return {"msg": f"Error adding project: {e}"}, 500


@project_ns.route("/<string:project_id>/view")
class ProjectView(Resource):
    @jwt_required()
    @project_ns.marshal_with(project_response)
    def get(self, project_id):
        current_user = get_jwt_identity()
        logger.info(
            f"Request to view project: {project_id}", extra={"login": current_user}
        )
        try:
            project_id = UUID(project_id)
            from app.database.managers.projects_managers import ProjectsManager

            db = ProjectsManager()
            project = db.get_by_id(project_id)
            if not project:
                logger.warning(
                    f"Project {project_id} not found", extra={"login": current_user}
                )
                return {"msg": "Project not found"}, 404
            return {"msg": "Project found successfully", "project": project}, 200
        except Exception as e:
            logger.error(f"Error viewing project: {e}", extra={"login": current_user})
            return {"msg": f"Error viewing project: {e}"}, 500


@project_ns.route("/<string:project_id>/delete/soft")
class ProjectSoftDelete(Resource):
    @jwt_required()
    @user_forbidden
    @project_ns.marshal_with(project_msg_model)
    def patch(self, project_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to soft delete project: {project_id}",
            extra={"login": current_user},
        )
        try:
            project_id = UUID(project_id)
            from app.database.managers.projects_managers import ProjectsManager

            db = ProjectsManager()

            project = db.get_by_id(record_id=project_id)
            if (
                project["project_leader"] != current_user["user_id"]  # type: ignore
                and current_user["role"] == "project-leader"
            ):
                logger.warning(
                    "Trying to soft delete not user's project",
                    extra={"login": current_user},
                )
                return {"msg": "User cannot hard delete not his shift report"}, 403

            updated = db.update(record_id=project_id, deleted=True)
            if not updated:
                logger.warning(
                    f"Project {project_id} not found for soft delete",
                    extra={"login": current_user},
                )
                return {"msg": "Project not found"}, 404
            return {
                "msg": f"Project {project_id} soft deleted successfully",
                "project_id": project_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error soft deleting project: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error soft deleting project: {e}"}, 500


@project_ns.route("/<string:project_id>/delete/hard")
class ProjectHardDelete(Resource):
    @jwt_required()
    @user_forbidden
    @project_ns.marshal_with(project_msg_model)
    def delete(self, project_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to hard delete project: {project_id}",
            extra={"login": current_user},
        )
        try:
            project_id = UUID(project_id)
            from app.database.managers.projects_managers import ProjectsManager

            db = ProjectsManager()

            project = db.get_by_id(record_id=project_id)
            if (
                project["project_leader"] != current_user["user_id"]  # type: ignore
                and current_user["role"] == "project-leader"
            ):
                logger.warning(
                    "Trying to hard delete not user's project",
                    extra={"login": current_user},
                )
                return {"msg": "User cannot hard delete not his shift report"}, 403

            deleted = db.delete(record_id=project_id)
            if not deleted:
                logger.warning(
                    f"Project {project_id} not found for hard delete",
                    extra={"login": current_user},
                )
                return {"msg": "Project not found"}, 404

            return {
                "msg": f"Project {project_id} hard deleted successfully",
                "project_id": project_id,
            }, 200
        except IntegrityError:
            logger.warning(
                f"Conflict: dependent data exists for project {project_id}",
                extra={"login": current_user},
            )
            abort(409, description="Cannot delete project: dependent data exists.")
        except Exception as e:
            logger.error(
                f"Error hard deleting project: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error hard deleting project: {e}"}, 500


@project_ns.route("/<string:project_id>/edit")
class ProjectEdit(Resource):
    @jwt_required()
    @user_forbidden
    @project_ns.expect(project_create_model)
    @project_ns.marshal_with(project_msg_model)
    def patch(self, project_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to edit project: {project_id}", extra={"login": current_user}
        )
        logger.debug(
            f"Received PATCH request: {request.json}", extra={"login": current_user}
        )

        schema = ProjectEditSchema()
        try:
            data = schema.load(request.json)  # type: ignore
            logger.info("Validation successful", extra={"login": current_user})
        except ValidationError as err:
            logger.error(
                f"Validation error: {err.messages}", extra={"login": current_user}
            )
            return {"error": err.messages}, 400
        try:
            project_id = UUID(project_id)
            from app.database.managers.projects_managers import ProjectsManager

            db = ProjectsManager()

            project = db.get_by_id(record_id=project_id)
            if (
                project["project_leader"] != current_user["user_id"]  # type: ignore
                and current_user["role"] == "project-leader"
            ):
                logger.warning(
                    "Trying to edit not user's project", extra={"login": current_user}
                )
                return {"msg": "User cannot edit not his shift report"}, 403

            updated = db.update(record_id=project_id, **data)  # type: ignore
            if not updated:
                logger.warning(
                    f"Project {project_id} not found for edit",
                    extra={"login": current_user},
                )
                return {"msg": "Project not found"}, 404

            return {"msg": "Project edited successfully", "project_id": project_id}, 200
        except Exception as e:
            logger.error(f"Error editing project: {e}", extra={"login": current_user})
            return {"msg": f"Error editing project: {e}"}, 500


@project_ns.route("/all")
class ProjectAll(Resource):
    @jwt_required()
    @project_ns.expect(project_filter_parser)
    @project_ns.marshal_with(project_all_response)
    def get(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to fetch all projects", extra={"login": current_user})

        schema = ProjectFilterSchema()
        try:
            args = schema.load(request.args)
        except ValidationError as err:
            logger.error(
                f"Validation error: {err.messages}", extra={"login": current_user}
            )
            return {"error": err.messages}, 400

        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit", 10)  # type: ignore
        sort_by = args.get("sort_by")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore
        filters = {
            "name": args.get("name"),  # type: ignore
            "deleted": args.get("deleted"),  # type: ignore
            "object": args.get("object"),  # type: ignore
            "project_leader": args.get("project_leader"),  # type: ignore
            "created_by": args.get("created_by"),  # type: ignore
            "created_at": args.get("created_at"),  # type: ignore
        }

        logger.debug(
            f"Fetching projects with filters: {filters}, offset={offset}, limit={
                limit
            }, sort_by={sort_by}, sort_order={sort_order}",
            extra={"login": current_user},
        )

        try:
            from app.database.managers.projects_managers import ProjectsManager

            db = ProjectsManager()
            projects = db.get_all_filtered_with_status(
                user=current_user,
                offset=offset,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order,
                **filters,
            )
            logger.info(
                f"Successfully fetched {len(projects)} projects",
                extra={"login": current_user},
            )
            return {"msg": "Projects found successfully", "projects": projects}, 200
        except Exception as e:
            logger.error(f"Error fetching projects: {e}", extra={"login": current_user})
            return {"msg": f"Error fetching projects: {e}"}, 500


@project_ns.route("/<string:project_id>/get-stat")
class ProjectStats(Resource):
    @jwt_required()
    @project_ns.marshal_with(project_stats_response)
    def get(self, project_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to view stats of project: {project_id}",
            extra={"login": current_user},
        )
        try:
            project_id = UUID(project_id)
        except ValueError as exc:
            raise ValueError("Invalid UUID format") from exc
        from app.database.managers.projects_managers import ProjectsManager

        db = ProjectsManager()
        try:
            stats = db.get_project_stats(project_id)
            if not stats:
                logger.warning(
                    f"Stats not found for project {project_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Stats not found", "stats": {}}, 200
            return {"msg": "Project stats fetched successfully", "stats": stats}, 200
        except Exception as e:
            logger.error(
                f"Error getting stats for project: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error getting stats for project: {e}"}, 500


@project_ns.route("/<string:project_id>/get-stat-by-project-work")
class ProjectStatsByProjectWork(Resource):
    @jwt_required()
    @project_ns.marshal_with(project_stats_response)
    def get(self, project_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to get project stats BY PROJECT WORK for project: {project_id}",
            extra={"login": current_user},
        )
        try:
            project_id = UUID(project_id)
        except ValueError as exc:
            raise ValueError("Invalid UUID format") from exc

        from app.database.managers.projects_managers import ProjectsManager

        db = ProjectsManager()

        try:
            stats = db.get_project_stats_by_project_work(project_id)
            if not stats:
                logger.warning(
                    f"No stats BY PROJECT WORK found for project {project_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Stats not found", "stats": {}}, 200
            logger.info(
                f"Stats BY PROJECT WORK successfully fetched for project {project_id}",
                extra={"login": current_user},
            )
            return {"msg": "Project stats fetched successfully", "stats": stats}, 200
        except Exception as e:
            logger.error(
                f"Error getting stats BY PROJECT WORK for project {project_id}: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error getting stats for project: {e}"}, 500
