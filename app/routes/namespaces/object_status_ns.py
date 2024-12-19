import json
import logging
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.routes.models.object_status_models import (
    object_status_create_model,
    object_status_msg_model,
    object_status_response,
    object_status_all_response,
    object_status_filter_parser,
    object_status_model
)

logger = logging.getLogger('ok_service')

object_status_ns = Namespace(
    'object_statuses', description='Object Status management operations')

object_status_ns.models[object_status_create_model.name] = object_status_create_model
object_status_ns.models[object_status_msg_model.name] = object_status_msg_model
object_status_ns.models[object_status_response.name] = object_status_response
object_status_ns.models[object_status_all_response.name] = object_status_all_response
object_status_ns.models[object_status_model.name] = object_status_model


@object_status_ns.route('/add')
class ObjectStatusAdd(Resource):
    @jwt_required()
    @object_status_ns.expect(object_status_create_model)
    @object_status_ns.marshal_with(object_status_msg_model)
    @object_status_ns.response(400, "Bad request, invalid data.")
    @object_status_ns.response(500, "Internal Server Error")
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            "Запрос на добавление нового статуса объекта.",
            extra={"login": current_user.get('login')}
        )

        object_status_id = request.json.get("object_status_id")
        name = request.json.get("name")

        # Логирование входных данных
        logger.debug(f"Параметры добавления статуса: object_status_id={object_status_id}, name={name}",
                     extra={"login": current_user.get('login')}
                     )

        if not (object_status_id and name):
            logger.warning("Отсутствуют обязательные параметры для добавления статуса объекта",
                           extra={"login": current_user.get('login')})
            return {"msg": "Bad request, invalid data."}, 400
        try:
            from app.database.managers.objects_managers import ObjectStatusesManager
            db = ObjectStatusesManager()
            logger.debug("Добавление статуса объекта в базу...",
                         extra={"login": current_user.get('login')})
            db.add(object_status_id=object_status_id, name=name)
            logger.info(
                f"Успешно добавлен новый статус объекта object_status_id={
                    object_status_id}",
                extra={"login": current_user.get('login')}
            )
            return {"msg": "New object status added successfully"}, 200
        except Exception as e:
            logger.error(
                f"Ошибка при добавлении статуса объекта: {e}",
                extra={"login": current_user.get('login')}
            )
            return {"msg": f"Error in adding object status: {e}"}, 500


@object_status_ns.route('/<string:object_status_id>/view')
class ObjectStatusView(Resource):
    @jwt_required()
    @object_status_ns.marshal_with(object_status_response)
    @object_status_ns.response(404, "Object status not found")
    @object_status_ns.response(500, "Internal Server Error")
    def get(self, object_status_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Запрос на просмотр статуса объекта object_status_id={
                object_status_id}",
            extra={"login": current_user.get('login')}
        )
        try:
            from app.database.managers.objects_managers import ObjectStatusesManager
            db = ObjectStatusesManager()
            logger.debug("Получение статуса объекта из базы...",
                         extra={"login": current_user.get('login')})
            object_status = db.get_by_id(object_status_id)
            if not object_status:
                logger.warning(f"Статус объекта object_status_id={object_status_id} не найден",
                               extra={"login": current_user.get('login')})
                return {"msg": "Object status not found"}, 404
            logger.info(f"Статус объекта object_status_id={object_status_id} найден успешно",
                        extra={"login": current_user.get('login')})
            return {"msg": "Object status found successfully", "object_status": object_status.to_dict()}, 200
        except Exception as e:
            logger.error(
                f"Ошибка при получении статуса объекта object_status_id={
                    object_status_id}: {e}",
                extra={"login": current_user.get('login')}
            )
            return {'msg': f"Error during getting object status: {e}"}, 500


@object_status_ns.route('/all')
class ObjectStatusAll(Resource):
    @jwt_required()
    @object_status_ns.expect(object_status_filter_parser)
    @object_status_ns.marshal_with(object_status_all_response)
    @object_status_ns.response(500, "Internal Server Error")
    def get(self):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            "Запрос на получение списка статусов объектов.",
            extra={"login": current_user.get('login')}
        )

        args = object_status_filter_parser.parse_args()
        offset = args.get('offset', 0)
        limit = args.get('limit', 10)
        sort_by = args.get('sort_by')
        sort_order = args.get('sort_order', 'asc')
        filters = {
            'object_status_id': args.get('object_status_id'),
            'name': args.get('name'),
        }

        logger.debug(
            f"Параметры фильтрации: offset={offset}, limit={limit}, sort_by={
                sort_by}, sort_order={sort_order}, filters={filters}",
            extra={"login": current_user.get('login')}
        )

        try:
            from app.database.managers.objects_managers import ObjectStatusesManager
            db = ObjectStatusesManager()
            logger.debug("Получение списка статусов объектов из базы...", extra={
                         "login": current_user.get('login')})
            object_statuses = db.get_all_filtered(
                offset, limit, sort_by, sort_order, **filters)
            logger.info(
                f"Успешно получен список статусов объектов: количество={
                    len(object_statuses)}",
                extra={"login": current_user.get('login')}
            )
            return {"object_statuses": [os.to_dict() for os in object_statuses], "msg": "Object statuses found successfully"}, 200
        except Exception as e:
            logger.error(
                f"Ошибка при получении списка статусов объектов: {e}",
                extra={"login": current_user.get('login')}
            )
            return {'msg': f"Error during getting object statuses: {e}"}, 500


@object_status_ns.route('/<string:object_status_id>/delete/hard')
class ObjectStatusDeleteHard(Resource):
    @jwt_required()
    @object_status_ns.marshal_with(object_status_msg_model)
    @object_status_ns.response(404, "Object status not found")
    @object_status_ns.response(500, "Internal Server Error")
    def delete(self, object_status_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Запрос на окончательное удаление статуса объекта object_status_id={object_status_id}",
                    extra={"login": current_user.get('login')})
        try:
            from app.database.managers.objects_managers import ObjectStatusesManager
            db = ObjectStatusesManager()
            logger.debug("Удаление статуса объекта из базы...",
                         extra={"login": current_user.get('login')})
            deleted = db.delete(record_id=object_status_id)
            if not deleted:
                logger.warning(f"Статус объекта object_status_id={object_status_id} не найден при hard удалении",
                               extra={"login": current_user.get('login')})
                return {"msg": "Object status not found"}, 404
            logger.info(f"Статус объекта object_status_id={object_status_id} удален окончательно",
                        extra={"login": current_user.get('login')})
            return {"msg": f"Object status {object_status_id} hard deleted successfully"}, 200
        except Exception as e:
            logger.error(
                f"Ошибка при окончательном удалении статуса объекта object_status_id={
                    object_status_id}: {e}",
                extra={"login": current_user.get('login')}
            )
            return {'msg': f"Error during hard deleting object status: {e}"}, 500


@object_status_ns.route('/<string:object_status_id>/edit')
class ObjectStatusEdit(Resource):
    @jwt_required()
    @object_status_ns.expect(object_status_create_model)
    @object_status_ns.marshal_with(object_status_msg_model)
    @object_status_ns.response(400, "Bad request, invalid data.")
    @object_status_ns.response(404, "Object status not found")
    @object_status_ns.response(500, "Internal Server Error")
    def patch(self, object_status_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Запрос на редактирование статуса объекта object_status_id={
                object_status_id}",
            extra={"login": current_user.get('login')}
        )

        name = request.json.get("name")

        # Логирование входных данных
        logger.debug(
            f"Параметры редактирования статуса объекта: name={name}",
            extra={"login": current_user.get('login')}
        )

        if not name:
            logger.warning(f"Отсутствуют обязательные параметры для редактирования статуса объекта object_status_id={object_status_id}",
                           extra={"login": current_user.get('login')})
            return {"msg": "Bad request, invalid data."}, 400

        try:
            from app.database.managers.objects_managers import ObjectStatusesManager
            db = ObjectStatusesManager()
            logger.debug("Обновление данных статуса объекта в базе...", extra={
                         "login": current_user.get('login')})
            updated = db.update(record_id=object_status_id, name=name)
            if not updated:
                logger.warning(f"Статус объекта object_status_id={object_status_id} не найден при редактировании",
                               extra={"login": current_user.get('login')})
                return {"msg": "Object status not found"}, 404

            logger.info(f"Успешно отредактирован статус объекта object_status_id={object_status_id}",
                        extra={"login": current_user.get('login')}
                        )
            return {"msg": "Object status edited successfully"}, 200
        except Exception as e:
            logger.error(
                f"Ошибка при редактировании статуса объекта object_status_id={
                    object_status_id}: {e}",
                extra={"login": current_user.get('login')}
            )
            return {"msg": f"Error in editing object status: {e}"}, 500
