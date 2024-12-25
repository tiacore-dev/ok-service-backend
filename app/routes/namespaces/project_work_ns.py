import logging
from uuid import UUID
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.routes.models.project_work_models import (
    project_work_create_model,
    project_work_msg_model,
    project_work_response,
    project_work_all_response,
    project_work_filter_parser,
    project_work_model,
    work_model
)

logger = logging.getLogger('ok_service')

project_work_ns = Namespace(
    'project_works', description='Project Works management operations')

# Инициализация моделей
project_work_ns.models[project_work_create_model.name] = project_work_create_model
project_work_ns.models[project_work_msg_model.name] = project_work_msg_model
project_work_ns.models[project_work_response.name] = project_work_response
project_work_ns.models[project_work_all_response.name] = project_work_all_response
project_work_ns.models[project_work_model.name] = project_work_model
project_work_ns.models[work_model.name] = work_model


@project_work_ns.route('/add')
class ProjectWorkAdd(Resource):
    @jwt_required()
    @project_work_ns.expect(project_work_create_model)
    @project_work_ns.marshal_with(project_work_msg_model)
    def post(self):
        current_user = get_jwt_identity()
        logger.info("Request to add new project work",
                    extra={"login": current_user})

        data = request.json
        try:
            from app.database.managers.projects_managers import ProjectWorksManager
            db = ProjectWorksManager()

            new_project_work = db.add(**data)
            logger.info(f"New project work added: {new_project_work['project_work_id']}",
                        extra={"login": current_user})
            return {"msg": "New project work added successfully"}, 200
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
    @project_work_ns.marshal_with(project_work_msg_model)
    def patch(self, project_work_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to soft delete project work: {project_work_id}",
                    extra={"login": current_user})

        try:
            project_work_id = UUID(project_work_id)
            from app.database.managers.projects_managers import ProjectWorksManager
            db = ProjectWorksManager()
            updated = db.update(record_id=project_work_id, signed=False)
            if not updated:
                return {"msg": "Project work not found"}, 404
            return {"msg": f"Project work {project_work_id} soft deleted successfully"}, 200
        except Exception as e:
            logger.error(f"Error soft deleting project work: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error soft deleting project work: {e}"}, 500


@project_work_ns.route('/<string:project_work_id>/delete/hard')
class ProjectWorkHardDelete(Resource):
    @jwt_required()
    @project_work_ns.marshal_with(project_work_msg_model)
    def delete(self, project_work_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to hard delete project work: {project_work_id}",
                    extra={"login": current_user})

        try:
            project_work_id = UUID(project_work_id)
            from app.database.managers.projects_managers import ProjectWorksManager
            db = ProjectWorksManager()
            deleted = db.delete(record_id=project_work_id)
            if not deleted:
                return {"msg": "Project work not found"}, 404
            return {"msg": f"Project work {project_work_id} hard deleted successfully"}, 200
        except Exception as e:
            logger.error(f"Error hard deleting project work: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error hard deleting project work: {e}"}, 500


@project_work_ns.route('/<string:project_work_id>/edit')
class ProjectWorkEdit(Resource):
    @jwt_required()
    @project_work_ns.expect(project_work_create_model)
    @project_work_ns.marshal_with(project_work_msg_model)
    def patch(self, project_work_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to edit project work: {project_work_id}",
                    extra={"login": current_user})

        data = request.json
        try:
            project_work_id = UUID(project_work_id)
            from app.database.managers.projects_managers import ProjectWorksManager
            db = ProjectWorksManager()
            updated = db.update(record_id=project_work_id, **data)
            if not updated:
                return {"msg": "Project work not found"}, 404
            return {"msg": "Project work edited successfully"}, 200
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

        args = project_work_filter_parser.parse_args()
        offset = args.get('offset', 0)
        limit = args.get('limit', None)
        sort_by = args.get('sort_by')
        sort_order = args.get('sort_order', 'asc')
        filters = {
            'signed': args.get('signed'),
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
