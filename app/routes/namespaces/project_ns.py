import logging
from uuid import UUID
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.routes.models.project_models import (
    project_create_model,
    project_msg_model,
    project_response,
    project_all_response,
    project_filter_parser,
    project_model,
    object_model,
    user_model
)

logger = logging.getLogger('ok_service')

project_ns = Namespace(
    'projects', description='Projects management operations')

# Инициализация моделей
project_ns.models[project_create_model.name] = project_create_model
project_ns.models[project_msg_model.name] = project_msg_model
project_ns.models[project_response.name] = project_response
project_ns.models[project_all_response.name] = project_all_response
project_ns.models[project_model.name] = project_model
project_ns.models[object_model.name] = object_model
project_ns.models[user_model.name] = user_model


@project_ns.route('/add')
class ProjectAdd(Resource):
    @jwt_required()
    @project_ns.expect(project_create_model)
    @project_ns.marshal_with(project_msg_model)
    def post(self):
        current_user = get_jwt_identity()
        logger.info("Request to add new project",
                    extra={"login": current_user})

        data = request.json
        try:
            from app.database.managers.projects_managers import ProjectsManager
            db = ProjectsManager()

            # Добавление проекта
            new_project = db.add(**data)  # Возвращается словарь
            logger.info(f"New project added: {new_project['project_id']}",
                        extra={"login": current_user})
            return {"msg": "New project added successfully"}, 200
        except Exception as e:
            logger.error(f"Error adding project: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error adding project: {e}"}, 500


@project_ns.route('/<string:project_id>/view')
class ProjectView(Resource):
    @jwt_required()
    @project_ns.marshal_with(project_response)
    def get(self, project_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to view project: {project_id}",
                    extra={"login": current_user})
        try:
            try:
                # Конвертируем строку в UUID
                project_id = UUID(project_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.projects_managers import ProjectsManager
            db = ProjectsManager()
            project = db.get_by_id(project_id)
            if not project:
                return {"msg": "Project not found"}, 404
            return {"msg": "Project found successfully", "project": project}, 200
        except Exception as e:
            logger.error(f"Error viewing project: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error viewing project: {e}"}, 500


@project_ns.route('/<string:project_id>/delete/soft')
class ProjectSoftDelete(Resource):
    @jwt_required()
    @project_ns.marshal_with(project_msg_model)
    def patch(self, project_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to soft delete project: {project_id}",
                    extra={"login": current_user})
        try:
            try:
                # Конвертируем строку в UUID
                project_id = UUID(project_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.projects_managers import ProjectsManager
            db = ProjectsManager()
            updated = db.update(record_id=project_id, deleted=True)
            if not updated:
                return {"msg": "Project not found"}, 404
            return {"msg": f"Project {project_id} soft deleted successfully"}, 200
        except Exception as e:
            logger.error(f"Error soft deleting project: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error soft deleting project: {e}"}, 500


@project_ns.route('/<string:project_id>/delete/hard')
class ProjectHardDelete(Resource):
    @jwt_required()
    @project_ns.marshal_with(project_msg_model)
    def delete(self, project_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to hard delete project: {project_id}",
                    extra={"login": current_user})
        try:
            try:
                # Конвертируем строку в UUID
                project_id = UUID(project_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.projects_managers import ProjectsManager
            db = ProjectsManager()
            deleted = db.delete(record_id=project_id)
            if not deleted:
                return {"msg": "Project not found"}, 404
            return {"msg": f"Project {project_id} hard deleted successfully"}, 200
        except Exception as e:
            logger.error(f"Error hard deleting project: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error hard deleting project: {e}"}, 500


@project_ns.route('/<string:project_id>/edit')
class ProjectEdit(Resource):
    @jwt_required()
    @project_ns.expect(project_create_model)
    @project_ns.marshal_with(project_msg_model)
    def patch(self, project_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to edit project: {project_id}",
                    extra={"login": current_user})

        data = request.json
        try:
            try:
                # Конвертируем строку в UUID
                project_id = UUID(project_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.projects_managers import ProjectsManager
            db = ProjectsManager()
            updated = db.update(record_id=project_id, **data)
            if not updated:
                return {"msg": "Project not found"}, 404
            return {"msg": "Project edited successfully"}, 200
        except Exception as e:
            logger.error(f"Error editing project: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error editing project: {e}"}, 500


@project_ns.route('/all')
class ProjectAll(Resource):
    @jwt_required()
    @project_ns.expect(project_filter_parser)
    @project_ns.marshal_with(project_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info("Request to fetch all projects",
                    extra={"login": current_user})

        args = project_filter_parser.parse_args()
        offset = args.get('offset', 0)
        limit = args.get('limit', None)
        sort_by = args.get('sort_by')
        sort_order = args.get('sort_order', 'asc')
        filters = {
            'name': args.get('name'),
            'deleted': args.get('deleted'),
        }

        logger.debug(f"Fetching projects with filters: {filters}, offset={offset}, limit={limit}, sort_by={sort_by}, sort_order={sort_order}",
                     extra={"login": current_user})

        try:
            from app.database.managers.projects_managers import ProjectsManager
            db = ProjectsManager()
            projects = db.get_all_filtered(
                offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order, **filters)
            logger.info(f"Successfully fetched {len(projects)} projects",
                        extra={"login": current_user})
            return {"msg": "Projects found successfully", "projects": projects}, 200
        except Exception as e:
            logger.error(f"Error fetching projects: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error fetching projects: {e}"}, 500
