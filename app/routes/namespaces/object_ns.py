import logging
import json
from uuid import UUID
from flask import request
from flask import abort
from sqlalchemy.exc import IntegrityError
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app.schemas.object_schemas import ObjectCreateSchema, ObjectFilterSchema, ObjectEditSchema
from app.routes.models.object_models import (
    object_create_model,
    object_msg_model,
    object_response,
    object_all_response,
    object_filter_parser,
    object_model
)


logger = logging.getLogger('ok_service')

object_ns = Namespace('objects', description='Objects management operations')

# Инициализация моделей
object_ns.models[object_create_model.name] = object_create_model
object_ns.models[object_msg_model.name] = object_msg_model
object_ns.models[object_response.name] = object_response
object_ns.models[object_all_response.name] = object_all_response
object_ns.models[object_model.name] = object_model


@object_ns.route('/add')
class ObjectAdd(Resource):
    @jwt_required()
    @object_ns.expect(object_create_model)
    @object_ns.marshal_with(object_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.debug(f"Decoded JWT Identity: {current_user}")
        if current_user['role'] != 'admin':
            logger.warning("Несанкционированный запрос на добавление нового объекта.",
                           extra={"login": current_user.get('login')}
                           )
            return {"msg": "Forbidden"}, 403
        logger.info("Request to add new object", extra={"login": current_user})
        from app.database.managers.objects_managers import ObjectStatusesManager
        db_s = ObjectStatusesManager()
        data = request.json
        object_status_id = data.get("status")
        if not db_s.exists_by_id(record_id=object_status_id):
            return {"msg": "Invalid object status"}, 400
        schema = ObjectCreateSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        try:
            from app.database.managers.objects_managers import ObjectsManager
            db = ObjectsManager()

            # Добавление объекта
            # Возвращается словарь
            new_object = db.add(created_by=current_user['user_id'], **data)
            logger.info(f"New object added: {new_object['object_id']}",
                        extra={"login": current_user})
            return {"msg": "New object added successfully", "object_id": new_object['object_id']}, 200
        except Exception as e:
            logger.error(f"Error adding object: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error adding object: {e}"}, 500


@object_ns.route('/<string:object_id>/view')
class ObjectView(Resource):
    @jwt_required()
    @object_ns.marshal_with(object_response)
    def get(self, object_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Request to view object: {object_id}",
                    extra={"login": current_user})
        try:
            try:
                # Конвертируем строку в UUID
                object_id = UUID(object_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc
            from app.database.managers.objects_managers import ObjectsManager
            db = ObjectsManager()
            obj = db.get_by_id(object_id)
            if not obj:
                return {"msg": "Object not found"}, 404
            if current_user['role'] == 'user' and obj['status'] != 'active':
                return {"msg": "Forbidden"}, 403
            return {"msg": "Object found successfully", "object": obj}, 200
        except Exception as e:
            logger.error(f"Error viewing object: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error viewing object: {e}"}, 500


@object_ns.route('/<string:object_id>/delete/soft')
class ObjectSoftDelete(Resource):
    @jwt_required()
    @object_ns.marshal_with(object_msg_model)
    def patch(self, object_id):
        current_user = json.loads(get_jwt_identity())
        logger.debug(f"Decoded JWT Identity: {current_user}")
        if current_user['role'] != 'admin':
            logger.warning("Несанкционированный запрос на мягкое удаление объекта.",
                           extra={"login": current_user.get('login')}
                           )
            return {"msg": "Forbidden"}, 403
        logger.info(f"Request to soft delete object: {object_id}",
                    extra={"login": current_user})
        try:
            # Пример обработки UUID, полученного как строка
            try:
                # Конвертируем строку в UUID
                object_id = UUID(object_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc
            from app.database.managers.objects_managers import ObjectsManager
            db = ObjectsManager()
            updated = db.update(record_id=object_id, deleted=True)
            if not updated:
                return {"msg": "Object not found"}, 404
            return {"msg": f"Object {object_id} soft deleted successfully", "object_id": object_id}, 200
        except Exception as e:
            logger.error(f"Error soft deleting object: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error soft deleting object: {e}"}, 500


@object_ns.route('/<string:object_id>/delete/hard')
class ObjectHardDelete(Resource):
    @jwt_required()
    @object_ns.marshal_with(object_msg_model)
    def delete(self, object_id):
        current_user = json.loads(get_jwt_identity())
        logger.debug(f"Decoded JWT Identity: {current_user}")
        if current_user['role'] != 'admin':
            logger.warning("Несанкционированный запрос на удаление (hard) объекта.",
                           extra={"login": current_user.get('login')}
                           )
            return {"msg": "Forbidden"}, 403
        logger.info(f"Request to hard delete object: {object_id}",
                    extra={"login": current_user})
        try:
            try:
                # Конвертируем строку в UUID
                object_id = UUID(object_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc
            from app.database.managers.objects_managers import ObjectsManager
            db = ObjectsManager()
            deleted = db.delete(record_id=object_id)
            if not deleted:
                return {"msg": "Object not found"}, 404
            return {"msg": f"Object {object_id} hard deleted successfully", "object_id": object_id}, 200
        except IntegrityError:
            abort(409, description="Cannot delete object: dependent data exists.")
        except Exception as e:
            logger.error(f"Error hard deleting object: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error hard deleting object: {e}"}, 500


@object_ns.route('/<string:object_id>/edit')
class ObjectEdit(Resource):
    @jwt_required()
    @object_ns.expect(object_create_model)
    @object_ns.marshal_with(object_msg_model)
    def patch(self, object_id):
        current_user = json.loads(get_jwt_identity())
        logger.debug(f"Decoded JWT Identity: {current_user}")
        if current_user['role'] != 'admin':
            logger.warning("Несанкционированный запрос на изменение объекта.",
                           extra={"login": current_user.get('login')}
                           )
            return {"msg": "Forbidden"}, 403
        logger.info(f"Request to edit object: {object_id}",
                    extra={"login": current_user})

        schema = ObjectEditSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            logger.error(f"Validation error: {err.messages}")
            return {"error": err.messages}, 400
        try:
            try:
                # Конвертируем строку в UUID
                object_id = UUID(object_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc
            from app.database.managers.objects_managers import ObjectsManager
            db = ObjectsManager()
            updated = db.update(record_id=object_id, **data)
            if not updated:
                return {"msg": "Object not found"}, 404
            return {"msg": "Object edited successfully", "object_id": object_id}, 200
        except Exception as e:
            logger.error(f"Error editing object: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error editing object: {e}"}, 500


@object_ns.route('/all')
class ObjectAll(Resource):
    @jwt_required()
    @object_ns.expect(object_filter_parser)  # Используем для Swagger
    @object_ns.marshal_with(object_all_response)
    def get(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to fetch all objects",
                    extra={"login": current_user})

        # Валидация query-параметров через Marshmallow
        schema = ObjectFilterSchema()
        try:
            data = schema.load(request.args)  # Валидируем query-параметры
        except ValidationError as err:
            logger.error(f"Validation error: {err.messages}", extra={
                         "login": current_user})
            return {"error": err.messages}, 400

        # Извлекаем отвалидированные данные
        offset = data.get('offset', 0)
        limit = data.get('limit', None)
        sort_by = data.get('sort_by')
        sort_order = data.get('sort_order', 'desc')
        filters = {
            'name': data.get('name'),
            'deleted': data.get('deleted'),
            'address': data.get('address'),
            'status': data.get('status'),
            'created_by': data.get('created_by'),
            'created_at': data.get('created_at'),
        }
        if current_user['role'] == 'user':
            filters['status'] = 'active'

        logger.debug(f"Fetching objects with filters: {filters}, offset={offset}, limit={limit}",
                     extra={"login": current_user})

        try:
            from app.database.managers.objects_managers import ObjectsManager
            db = ObjectsManager()
            objects = db.get_all_filtered(
                offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order, **filters)
            logger.info(f"Successfully fetched {len(objects)} objects",
                        extra={"login": current_user})
            return {"msg": "Objects found successfully", "objects": objects}, 200
        except Exception as e:
            logger.error(f"Error fetching objects: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error fetching objects: {e}"}, 500
