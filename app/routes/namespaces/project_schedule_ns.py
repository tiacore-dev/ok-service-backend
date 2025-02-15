# Namespace for ProjectSchedules
import logging
import json
from uuid import UUID
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app.schemas.project_schedule_schemas import ProjectScheduleCreateSchema, ProjectScheduleFilterSchema, ProjectScheduleEditSchema
from app.routes.models.project_schedule_models import (
    project_schedule_create_model,
    project_schedule_msg_model,
    project_schedule_response,
    project_schedule_all_response,
    project_schedule_filter_parser,
    project_schedule_model
)
from app.decorators import user_forbidden

logger = logging.getLogger('ok_service')

project_schedule_ns = Namespace(
    'project_schedules', description='Project schedules management operations')

# Initialize models
project_schedule_ns.models[project_schedule_create_model.name] = project_schedule_create_model
project_schedule_ns.models[project_schedule_msg_model.name] = project_schedule_msg_model
project_schedule_ns.models[project_schedule_response.name] = project_schedule_response
project_schedule_ns.models[project_schedule_all_response.name] = project_schedule_all_response
project_schedule_ns.models[project_schedule_model.name] = project_schedule_model


@project_schedule_ns.route('/add')
class ProjectScheduleAdd(Resource):
    @jwt_required()
    @user_forbidden
    @project_schedule_ns.expect(project_schedule_create_model)
    @project_schedule_ns.marshal_with(project_schedule_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to add new project schedule",
                    extra={"login": current_user})

        schema = ProjectScheduleCreateSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
            logger.info(f"Полученные данные: {data}")
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        try:
            from app.database.managers.projects_managers import ProjectSchedulesManager, ProjectsManager
            db = ProjectSchedulesManager()
            db_p = ProjectsManager()
            if current_user['role'] == 'project-leader':
                led_projects = db_p.get_all_filtered(
                    project_leader=current_user['user_id'])
                logger.info(f"Найденные projects: {led_projects}")
                led_project_ids = {p['project_id']
                                   # Собираем ID проектов
                                   for p in led_projects}
                if str(data['project']) not in led_project_ids:

                    logger.warning("Trying to add now own project schedule", extra={
                                   "login": current_user})
                    return {"msg": "You cannot add not your projects"}, 403

            # Returns a dictionary
            new_schedule = db.add(created_by=current_user['user_id'], **data)
            logger.info(f"New project schedule added: {new_schedule['project_schedule_id']}",
                        extra={"login": current_user})
            return {"msg": "New project schedule added successfully", "project_schedule_id": new_schedule['project_schedule_id']}, 200
        except Exception as e:
            logger.error(f"Error adding project schedule: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error adding project schedule: {e}"}, 500


@project_schedule_ns.route('/<string:schedule_id>/view')
class ProjectScheduleView(Resource):
    @jwt_required()
    @project_schedule_ns.marshal_with(project_schedule_response)
    def get(self, schedule_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to view project schedule: {schedule_id}",
                    extra={"login": current_user})
        try:
            try:
                schedule_id = UUID(schedule_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.projects_managers import ProjectSchedulesManager
            db = ProjectSchedulesManager()

            schedule = db.get_by_id(schedule_id)
            if not schedule:
                return {"msg": "Project schedule not found"}, 404
            return {"msg": "Project schedule found successfully", "project_schedule": schedule}, 200
        except Exception as e:
            logger.error(f"Error viewing project schedule: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error viewing project schedule: {e}"}, 500


@project_schedule_ns.route('/<string:schedule_id>/delete/hard')
class ProjectScheduleHardDelete(Resource):
    @jwt_required()
    @user_forbidden
    @project_schedule_ns.marshal_with(project_schedule_msg_model)
    def delete(self, schedule_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Request to hard delete project schedule: {schedule_id}",
                    extra={"login": current_user})
        try:
            try:
                schedule_id = UUID(schedule_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.projects_managers import ProjectSchedulesManager
            db = ProjectSchedulesManager()

            # Проверки по ролям
            schedule = db.get_by_id(record_id=schedule_id)
            if current_user['role'] == 'project-leader':
                led_schedules = db.get_schedule_ids_by_project_leader(
                    current_user['user_id'])
                if str(schedule_id) not in led_schedules:
                    logger.warning(f"Trying to soft delete not user's project schedule",
                                   extra={"login": current_user})
                    return {"msg": "Forbidden"}, 403

            deleted = db.delete(record_id=schedule_id)
            if not deleted:
                return {"msg": "Project schedule not found"}, 404
            return {"msg": f"Project schedule {schedule_id} hard deleted successfully", "project_schedule_id": schedule_id}, 200
        except Exception as e:
            logger.error(f"Error hard deleting project schedule: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error hard deleting project schedule: {e}"}, 500


@project_schedule_ns.route('/<string:schedule_id>/edit')
class ProjectScheduleEdit(Resource):
    @jwt_required()
    @user_forbidden
    @project_schedule_ns.expect(project_schedule_create_model)
    @project_schedule_ns.marshal_with(project_schedule_msg_model)
    def patch(self, schedule_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Request to edit project schedule: {schedule_id}",
                    extra={"login": current_user})

        schema = ProjectScheduleEditSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        try:
            try:
                schedule_id = UUID(schedule_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.projects_managers import ProjectSchedulesManager
            db = ProjectSchedulesManager()

            # Проверки по ролям
            schedule = db.get_by_id(record_id=schedule_id)
            if current_user['role'] == 'project-leader':
                led_schedules = db.get_schedule_ids_by_project_leader(
                    current_user['user_id'])
                if str(schedule_id) not in led_schedules:
                    logger.warning(f"Trying to edit not user's project schedule",
                                   extra={"login": current_user})
                    return {"msg": "Forbidden"}, 403

            updated = db.update(record_id=schedule_id, **data)
            if not updated:
                return {"msg": "Project schedule not found"}, 404
            return {"msg": "Project schedule updated successfully", "project_schedule_id": schedule_id}, 200
        except Exception as e:
            logger.error(f"Error editing project schedule: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error editing project schedule: {e}"}, 500


@project_schedule_ns.route('/all')
class ProjectScheduleAll(Resource):
    @jwt_required()
    @project_schedule_ns.expect(project_schedule_filter_parser)
    @project_schedule_ns.marshal_with(project_schedule_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info("Request to fetch all project schedules",
                    extra={"login": current_user})

        schema = ProjectScheduleFilterSchema()
        try:
            args = schema.load(request.args)  # Валидируем query-параметры
        except ValidationError as err:
            logger.error(f"Validation error: {err.messages}", extra={
                         "login": current_user})
            return {"error": err.messages}, 400
        offset = args.get('offset', 0)
        limit = args.get('limit', None)
        sort_by = args.get('sort_by')
        sort_order = args.get('sort_order', 'asc')
        filters = {
            'project': args.get('project'),
            'work': args.get('work'),
            'date': args.get('date'),
            'created_by': args.get('created_by'),
            'created_at': args.get('created_at'),
        }

        logger.debug(f"Fetching project schedules with filters: {filters}, offset={offset}, limit={limit}",
                     extra={"login": current_user})

        try:
            from app.database.managers.projects_managers import ProjectSchedulesManager
            db = ProjectSchedulesManager()
            schedules = db.get_all_filtered(
                offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order, **filters)
            logger.info(f"Successfully fetched {len(schedules)} project schedules",
                        extra={"login": current_user})
            return {"msg": "Project schedules found successfully", "project_schedules": schedules}, 200
        except Exception as e:
            logger.error(f"Error fetching project schedules: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error fetching project schedules: {e}"}, 500
