import logging
import json
from uuid import UUID
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app.schemas.project_work_schemas import ProjectWorkCreateSchema, ProjectWorkFilterSchema, ProjectWorkEditSchema
from app.routes.models.project_work_models import (
    project_work_create_model,
    project_work_msg_model,
    project_work_response,
    project_work_all_response,
    project_work_filter_parser,
    project_work_model
)
from app.decorators import user_forbidden

logger = logging.getLogger('ok_service')

project_work_ns = Namespace(
    'project_works', description='Project Works management operations')

# Инициализация моделей
project_work_ns.models[project_work_create_model.name] = project_work_create_model
project_work_ns.models[project_work_msg_model.name] = project_work_msg_model
project_work_ns.models[project_work_response.name] = project_work_response
project_work_ns.models[project_work_all_response.name] = project_work_all_response
project_work_ns.models[project_work_model.name] = project_work_model


@project_work_ns.route('/add')
class ProjectWorkAdd(Resource):
    @jwt_required()
    @user_forbidden
    @project_work_ns.expect(project_work_create_model)
    @project_work_ns.marshal_with(project_work_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to add new project work",
                    extra={"login": current_user})

        schema = ProjectWorkCreateSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        try:
            from app.database.managers.projects_managers import ProjectWorksManager, ProjectsManager
            db = ProjectWorksManager()
            db_p = ProjectsManager()
            if current_user['role'] == 'project-leader':
                data['signed'] = False
                led_projects = db_p.get_all_filtered(
                    project_leader=current_user['user_id'])
                led_project_ids = {p['project_id']
                                   # Собираем ID проектов
                                   for p in led_projects}
                if str(data['project']) not in led_project_ids:
                    logger.warning("Trying to add now own project work", extra={
                                   "login": current_user})
                    return {"msg": "You cannot add not your projects"}, 403

            new_project_work = db.add(
                created_by=current_user['user_id'], **data)
            logger.info(f"New project work added: {new_project_work['project_work_id']}",
                        extra={"login": current_user})
            return {"msg": "New project work added successfully", "project_work_id": new_project_work['project_work_id']}, 200
        except Exception as e:
            logger.error(f"Error adding project work: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error adding project work: {e}"}, 500


@project_work_ns.route('/<string:project_work_id>/view')
class ProjectWorkView(Resource):
    @jwt_required()
    @project_work_ns.marshal_with(project_work_response)
    def get(self, project_work_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to view project work: {project_work_id}",
                    extra={"login": current_user})

        try:
            project_work_id = UUID(project_work_id)
            from app.database.managers.projects_managers import ProjectWorksManager
            db = ProjectWorksManager()
            project_work = db.get_by_id(project_work_id)
            if not project_work:
                return {"msg": "Project work not found"}, 404
            return {"msg": "Project work found successfully", "project_work": project_work}, 200
        except Exception as e:
            logger.error(f"Error viewing project work: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error viewing project work: {e}"}, 500


@project_work_ns.route('/<string:project_work_id>/delete/soft')
class ProjectWorkSoftDelete(Resource):
    @jwt_required()
    @user_forbidden
    @project_work_ns.marshal_with(project_work_msg_model)
    def patch(self, project_work_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Request to soft delete project work: {project_work_id}",
                    extra={"login": current_user})

        try:
            project_work_id = UUID(project_work_id)
            from app.database.managers.projects_managers import ProjectWorksManager
            db = ProjectWorksManager()

            # Проверки по ролям
            project_work = db.get_by_id(record_id=project_work_id)
            if current_user['role'] == 'project-leader':
                led_project_works = db.get_work_ids_by_project_leader(
                    current_user['user_id'])
                if str(project_work_id) not in led_project_works:
                    logger.warning("Trying to soft delete not user's project_work",
                                   extra={"login": current_user})
                    return {"msg": "Forbidden"}, 403
                elif str(project_work_id) in led_project_works and project_work['signed'] is True:
                    logger.warning("Trying to soft delete signed shift report",
                                   extra={"login": current_user})
                    return {"msg": "User cannot soft delete signed shift report"}, 403

            updated = db.update(record_id=project_work_id, signed=False)
            if not updated:
                return {"msg": "Project work not found"}, 404
            return {"msg": f"Project work {project_work_id} soft deleted successfully", "project_work_id": project_work_id}, 200
        except Exception as e:
            logger.error(f"Error soft deleting project work: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error soft deleting project work: {e}"}, 500


@project_work_ns.route('/<string:project_work_id>/delete/hard')
class ProjectWorkHardDelete(Resource):
    @jwt_required()
    @user_forbidden
    @project_work_ns.marshal_with(project_work_msg_model)
    def delete(self, project_work_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Request to hard delete project work: {project_work_id}",
                    extra={"login": current_user})

        try:
            project_work_id = UUID(project_work_id)
            from app.database.managers.projects_managers import ProjectWorksManager
            db = ProjectWorksManager()

            project_work = db.get_by_id(record_id=project_work_id)
            if current_user['role'] == 'project-leader':
                led_project_works = db.get_work_ids_by_project_leader(
                    current_user['user_id'])
                if str(project_work_id) not in led_project_works:
                    logger.warning("Trying to soft delete not user's project_work",
                                   extra={"login": current_user})
                    return {"msg": "Forbidden"}, 403
                elif str(project_work_id) in led_project_works and project_work['signed'] is True:
                    logger.warning("Trying to soft delete signed shift report",
                                   extra={"login": current_user})
                    return {"msg": "User cannot soft delete signed shift report"}, 403

            deleted = db.delete(record_id=project_work_id)
            if not deleted:
                return {"msg": "Project work not found"}, 404
            return {"msg": f"Project work {project_work_id} hard deleted successfully", "project_work_id": project_work_id}, 200
        except Exception as e:
            logger.error(f"Error hard deleting project work: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error hard deleting project work: {e}"}, 500


@project_work_ns.route('/<string:project_work_id>/edit')
class ProjectWorkEdit(Resource):
    @jwt_required()
    @user_forbidden
    @project_work_ns.expect(project_work_create_model)
    @project_work_ns.marshal_with(project_work_msg_model)
    def patch(self, project_work_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Request to edit project work: {project_work_id}",
                    extra={"login": current_user})

        schema = ProjectWorkEditSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        try:
            project_work_id = UUID(project_work_id)
            from app.database.managers.projects_managers import ProjectWorksManager
            db = ProjectWorksManager()

            project_work = db.get_by_id(record_id=project_work_id)
            if current_user['role'] == 'project-leader':
                led_project_works = db.get_work_ids_by_project_leader(
                    current_user['user_id'])
                logger.debug(f"DEBUG: Project leader {current_user['user_id']} управляет работами: {led_project_works}",
                             extra={"login": current_user})

                logger.debug(f"DEBUG: Проверяем работу {project_work_id} в списке работ лидера",
                             extra={"login": current_user})
                if str(project_work_id) not in led_project_works:
                    logger.warning("Trying to soft delete not user's project_work",
                                   extra={"login": current_user})
                    return {"msg": "Forbidden"}, 403
                elif str(project_work_id) in led_project_works and project_work['signed'] is True:
                    logger.warning("Trying to soft delete signed shift report",
                                   extra={"login": current_user})
                    return {"msg": "User cannot soft delete signed shift report"}, 403

            updated = db.update(record_id=project_work_id, **data)
            if not updated:
                return {"msg": "Project work not found"}, 404
            return {"msg": "Project work edited successfully", "project_work_id": project_work_id}, 200
        except Exception as e:
            logger.error(f"Error editing project work: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error editing project work: {e}"}, 500


@project_work_ns.route('/all')
class ProjectWorkAll(Resource):
    @jwt_required()
    @project_work_ns.expect(project_work_filter_parser)
    @project_work_ns.marshal_with(project_work_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info("Request to fetch all project works",
                    extra={"login": current_user})

        # Валидация query-параметров через Marshmallow
        schema = ProjectWorkFilterSchema()
        try:
            args = schema.load(request.args)  # Валидируем query-параметры
        except ValidationError as err:
            logger.error(f"Validation error: {err.messages}", extra={
                         "login": current_user})
            return {"error": err.messages}, 400
        offset = args.get('offset', 0)
        limit = args.get('limit', None)
        sort_by = args.get('sort_by')
        sort_order = args.get('sort_order', 'desc')
        filters = {
            'signed': args.get('signed'),
            'project': args.get('project'),
            'work': args.get('work'),
            'min_quantity': args.get('min_quantity'),
            'max_quantity': args.get('max_quantity'),
            'min_summ': args.get('min_summ'),
            'max_summ': args.get('max_summ'),
            'created_by': args.get('created_by'),
            'created_at': args.get('created_at'),
        }

        logger.debug(f"Fetching project works with filters: {filters}, offset={offset}, limit={limit}, sort_by={sort_by}, sort_order={sort_order}",
                     extra={"login": current_user})

        try:
            from app.database.managers.projects_managers import ProjectWorksManager
            db = ProjectWorksManager()
            project_works = db.get_all_filtered(
                offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order, **filters)
            logger.info(f"Successfully fetched {len(project_works)} project works",
                        extra={"login": current_user})
            return {"msg": "Project works found successfully", "project_works": project_works}, 200
        except Exception as e:
            logger.error(f"Error fetching project works: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error fetching project works: {e}"}, 500
