import logging
from uuid import UUID
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
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
        current_user = get_jwt_identity()
        logger.info("Request to add new object", extra={"login": current_user})

        data = request.json
        try:
            from app.database.managers.objects_managers import ObjectsManager
            db = ObjectsManager()

            # Добавление объекта
            new_object = db.add(**data)  # Возвращается словарь
            logger.info(f"New object added: {new_object['object_id']}",
                        extra={"login": current_user})
            return {"msg": "New object added successfully"}, 200
        except Exception as e:
            logger.error(f"Error adding object: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error adding object: {e}"}, 500


@object_ns.route('/<string:object_id>/view')
class ObjectView(Resource):
    @jwt_required()
    @object_ns.marshal_with(object_response)
    def get(self, object_id):
        current_user = get_jwt_identity()
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
        current_user = get_jwt_identity()
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
            return {"msg": f"Object {object_id} soft deleted successfully"}, 200
        except Exception as e:
            logger.error(f"Error soft deleting object: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error soft deleting object: {e}"}, 500


@object_ns.route('/<string:object_id>/delete/hard')
class ObjectHardDelete(Resource):
    @jwt_required()
    @object_ns.marshal_with(object_msg_model)
    def delete(self, object_id):
        current_user = get_jwt_identity()
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
            return {"msg": f"Object {object_id} hard deleted successfully"}, 200
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
        current_user = get_jwt_identity()
        logger.info(f"Request to edit object: {object_id}",
                    extra={"login": current_user})

        data = request.json
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
            return {"msg": "Object edited successfully"}, 200
        except Exception as e:
            logger.error(f"Error editing object: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error editing object: {e}"}, 500


@object_ns.route('/all')
class ObjectAll(Resource):
    @jwt_required()
    @object_ns.expect(object_filter_parser)
    @object_ns.marshal_with(object_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info("Request to fetch all objects",
                    extra={"login": current_user})

        args = object_filter_parser.parse_args()
        offset = args.get('offset', 0)
        limit = args.get('limit', None)
        sort_by = args.get('sort_by')
        sort_order = args.get('sort_order', 'asc')
        filters = {
            'name': args.get('name'),
            'deleted': args.get('deleted'),
        }

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
