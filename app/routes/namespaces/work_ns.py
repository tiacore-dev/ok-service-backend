import logging
import json
from uuid import UUID
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app.schemas.work_schemas import WorkCreateSchema, WorkFilterSchema, WorkEditSchema
from app.routes.models.work_models import (
    work_create_model,
    work_msg_model,
    work_response,
    work_all_response,
    work_filter_parser,
    work_model
)
from app.decorators import admin_required

logger = logging.getLogger('ok_service')

work_ns = Namespace('works', description='Works management operations')

# Инициализация моделей
work_ns.models[work_create_model.name] = work_create_model
work_ns.models[work_msg_model.name] = work_msg_model
work_ns.models[work_response.name] = work_response
work_ns.models[work_all_response.name] = work_all_response
work_ns.models[work_model.name] = work_model


@work_ns.route('/add')
class WorkAdd(Resource):
    @jwt_required()
    @admin_required
    @work_ns.expect(work_create_model)
    @work_ns.marshal_with(work_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to add new work", extra={"login": current_user})
        if current_user['role'] != 'admin':
            logger.warning("Несанкционированный запрос на добавление нового объекта.",
                           extra={"login": current_user.get('login')}
                           )
            return {"msg": "Forbidden"}, 403
        schema = WorkCreateSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        try:
            from app.database.managers.works_managers import WorksManager
            db = WorksManager()

            # Добавление работы
            new_work = db.add(created_by=current_user['user_id'], **data)
            logger.info(f"New work added: {new_work['work_id']}",
                        extra={"login": current_user})
            return {"msg": "New work added successfully", "work_id": new_work['work_id']}, 200
        except Exception as e:
            logger.error(f"Error adding work: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error adding work: {e}"}, 500


@work_ns.route('/<string:work_id>/view')
class WorkView(Resource):
    @jwt_required()
    @work_ns.marshal_with(work_response)
    def get(self, work_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to view work: {work_id}",
                    extra={"login": current_user})
        try:
            try:
                # Конвертируем строку в UUID
                work_id = UUID(work_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.works_managers import WorksManager
            db = WorksManager()
            work = db.get_by_id(work_id)
            if not work:
                return {"msg": "Work not found"}, 404
            return {"msg": "Work found successfully", "work": work}, 200
        except Exception as e:
            logger.error(f"Error viewing work: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error viewing work: {e}"}, 500


@work_ns.route('/<string:work_id>/delete/soft')
class WorkSoftDelete(Resource):
    @jwt_required()
    @admin_required
    @work_ns.marshal_with(work_msg_model)
    def patch(self, work_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Request to soft delete work: {work_id}",
                    extra={"login": current_user})
        try:
            try:
                # Конвертируем строку в UUID
                work_id = UUID(work_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.works_managers import WorksManager
            db = WorksManager()
            updated = db.update(record_id=work_id, deleted=True)
            if not updated:
                return {"msg": "Work not found"}, 404
            return {"msg": f"Work {work_id} soft deleted successfully", "work_id": work_id}, 200
        except Exception as e:
            logger.error(f"Error soft deleting work: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error soft deleting work: {e}"}, 500


@work_ns.route('/<string:work_id>/delete/hard')
class WorkHardDelete(Resource):
    @jwt_required()
    @admin_required
    @work_ns.marshal_with(work_msg_model)
    def delete(self, work_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Request to hard delete work: {work_id}",
                    extra={"login": current_user})
        try:
            try:
                # Конвертируем строку в UUID
                work_id = UUID(work_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.works_managers import WorksManager
            db = WorksManager()
            deleted = db.delete(record_id=work_id)
            if not deleted:
                return {"msg": "Work not found"}, 404
            return {"msg": f"Work {work_id} hard deleted successfully", "work_id": work_id}, 200
        except Exception as e:
            logger.error(f"Error hard deleting work: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error hard deleting work: {e}"}, 500


@work_ns.route('/<string:work_id>/edit')
class WorkEdit(Resource):
    @jwt_required()
    @admin_required
    @work_ns.expect(work_create_model)
    @work_ns.marshal_with(work_msg_model)
    def patch(self, work_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Request to edit work: {work_id}",
                    extra={"login": current_user})

        schema = WorkEditSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        try:
            try:
                # Конвертируем строку в UUID
                work_id = UUID(work_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.works_managers import WorksManager
            db = WorksManager()
            updated = db.update(record_id=work_id, **data)
            if not updated:
                return {"msg": "Work not found"}, 404
            return {"msg": "Work edited successfully", "work_id": work_id}, 200
        except Exception as e:
            logger.error(f"Error editing work: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error editing work: {e}"}, 500


@work_ns.route('/all')
class WorkAll(Resource):
    @jwt_required()
    @work_ns.expect(work_filter_parser)
    @work_ns.marshal_with(work_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info("Request to fetch all works",
                    extra={"login": current_user})

        # Валидация query-параметров через Marshmallow
        schema = WorkFilterSchema()
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
            'name': args.get('name'),
            'deleted': args.get('deleted'),
            'created_by': args.get('created_by'),
            'created_at': args.get('created_at'),
        }

        logger.debug(f"Fetching works with filters: {filters}, offset={offset}, limit={limit}, sort_by={sort_by}, sort_order={sort_order}",
                     extra={"login": current_user})

        try:
            from app.database.managers.works_managers import WorksManager
            db = WorksManager()
            works = db.get_all_filtered(
                offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order, **filters)
            logger.info(f"Successfully fetched {len(works)} works",
                        extra={"login": current_user})
            return {"msg": "Works found successfully", "works": works}, 200
        except Exception as e:
            logger.error(f"Error fetching works: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error fetching works: {e}"}, 500
