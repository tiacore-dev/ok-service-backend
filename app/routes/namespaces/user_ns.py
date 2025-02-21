import json
import logging
from uuid import UUID
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app.schemas.user_schemas import UserCreateSchema, UserFilterSchema, UserEditSchema
from app.routes.models.user_models import (
    user_create_model, user_msg_model,
    user_all_response, user_response,
    user_filter_parser, user_model
)

logger = logging.getLogger('ok_service')

user_ns = Namespace('users', description='User management operations')

user_ns.models[user_create_model.name] = user_create_model
user_ns.models[user_msg_model.name] = user_msg_model
user_ns.models[user_all_response.name] = user_all_response
user_ns.models[user_response.name] = user_response
user_ns.models[user_model.name] = user_model


@user_ns.route('/add')
class UserAdd(Resource):
    @jwt_required()
    @user_ns.expect(user_create_model)
    @user_ns.marshal_with(user_msg_model)
    @user_ns.response(400, "Bad request, invalid data.")
    @user_ns.response(500, "Internal Server Error")
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.debug(f"Decoded JWT Identity: {current_user}")
        if current_user['role'] != 'admin':
            logger.warning("Несанкционированный запрос на добавление нового пользователя.",
                           extra={"login": current_user.get('login')}
                           )
            return {"msg": "Forbidden"}, 403
        logger.info("Запрос на добавление нового пользователя.",
                    extra={"login": current_user.get('login')}
                    )
        schema = UserCreateSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        login = data.get('login')
        password = data.get("password")
        name = data.get("name")
        role = data.get("role")
        category = data.get("category")

        # Логируем входные данные
        logger.debug(f"Параметры добавления пользователя: login={login}, password={'*' if password else None}, name={name}, role={role}, category={category}",
                     extra={"login": current_user.get('login')})

        if not (login and password and name and role):
            logger.warning("Отсутствуют обязательные параметры для добавления пользователя",
                           extra={"login": current_user.get('login')})
            return {"msg": "Bad request, invalid data."}, 400
        try:
            from app.database.managers.user_manager import UserManager
            db = UserManager()
            logger.debug("Добавление пользователя в базу...",
                         extra={"login": current_user.get('login')})
            user_id = db.add_user(
                login=login, password=password, role=role, category=category, name=name, created_by=current_user['user_id'])
            logger.info(f"Успешно добавлен новый пользователь user_id={user_id}",
                        extra={"login": current_user.get('login')}
                        )
            return {"msg": "New user added successfully", "user_id": user_id}, 200
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя: {e}",
                         extra={"login": current_user.get('login')}
                         )
            return {"msg": f"Error in adding new user: {e}"}, 500


@user_ns.route('/<string:user_id>/view')
class UserView(Resource):
    @jwt_required()
    @user_ns.marshal_with(user_response)
    @user_ns.response(404, "User not found")
    @user_ns.response(500, "Internal Server Error")
    def get(self, user_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Запрос на просмотр пользователя user_id={user_id}",
                    extra={"login": current_user.get('login')})
        try:
            # Преобразуем строку в UUID
            try:
                user_id = UUID(user_id)
            except ValueError:
                return {"msg": "Invalid user ID format"}, 400
            from app.database.managers.user_manager import UserManager
            db = UserManager()
            logger.debug("Получение пользователя из базы...",
                         extra={"login": current_user.get('login')})
            user = db.get_by_id(user_id)
            if not user:
                logger.warning(f"Пользователь user_id={user_id} не найден",
                               extra={"login": current_user.get('login')})
                return {"msg": "User not found"}, 404
            logger.info(f"Пользователь user_id={user_id} найден успешно",
                        extra={"login": current_user.get('login')})
            return {"msg": "User found successfully", "user": user}, 200
        except Exception as e:
            logger.error(
                f"Ошибка при получении пользователя user_id={user_id}: {e}",
                extra={"login": current_user.get('login')}
            )
            return {'msg': f"Error during getting user: {e}"}, 500


@user_ns.route('/<string:user_id>/delete/soft')
class UserDeleteSoft(Resource):
    @jwt_required()
    @user_ns.marshal_with(user_msg_model)
    @user_ns.response(404, "User not found")
    @user_ns.response(500, "Internal Server Error")
    def patch(self, user_id):
        current_user = json.loads(get_jwt_identity())
        if current_user['role'] != 'admin':
            logger.warning(f"Несанкционированный запрос на мягкое удаление пользователя user_id={user_id}.",
                           extra={"login": current_user.get('login')}
                           )
            return {"msg": "Forbidden"}, 403
        logger.info(f"Запрос на мягкое удаление пользователя user_id={user_id}",
                    extra={"login": current_user.get('login')}
                    )
        try:
            # Преобразуем строку в UUID
            try:
                user_id = UUID(user_id)
            except ValueError:
                return {"msg": "Invalid user ID format"}, 400
            from app.database.managers.user_manager import UserManager
            db = UserManager()

            logger.debug("Обновление статуса deleted пользователя в базе...",
                         extra={"login": current_user.get('login')})
            updated = db.update(record_id=user_id, deleted=True)
            if not updated:
                logger.warning(f"Пользователь user_id={user_id} не найден при мягком удалении",
                               extra={"login": current_user.get('login')})
                return {"msg": "User not found"}, 404
            logger.info(f"Пользователь user_id={user_id} мягко удален",
                        extra={"login": current_user.get('login')})
            return {"msg": f"User {user_id} soft deleted successfully", "user_id": user_id}, 200
        except Exception as e:
            logger.error(f"Ошибка при мягком удалении пользователя user_id={user_id}: {e}",
                         extra={"login": current_user.get('login')}
                         )
            return {'msg': f"Error during soft deleting user: {e}"}, 500


@user_ns.route('/<string:user_id>/delete/hard')
class UserDeleteHard(Resource):
    @jwt_required()
    @user_ns.marshal_with(user_msg_model)
    @user_ns.response(404, "User not found")
    @user_ns.response(500, "Internal Server Error")
    def delete(self, user_id):
        current_user = json.loads(get_jwt_identity())
        if current_user['role'] != 'admin':
            logger.warning(f"Несанкционированный запрос на окончательное (hard) удаление пользователя user_id={user_id}.",
                           extra={"login": current_user.get('login')}
                           )
            return {"msg": "Forbidden"}, 403
        logger.info(f"Запрос на окончательное (hard) удаление пользователя user_id={user_id}",
                    extra={"login": current_user.get('login')}
                    )
        try:
            # Преобразуем строку в UUID
            try:
                user_id = UUID(user_id)
            except ValueError:
                return {"msg": "Invalid user ID format"}, 400
            from app.database.managers.user_manager import UserManager
            db = UserManager()
            logger.debug("Удаление пользователя из базы...",
                         extra={"login": current_user.get('login')})
            user = db.get_by_id(record_id=user_id)
            if user['created_by'] == user['user_id']:
                logger.warning(f"Попытка удлить админа",
                               extra={"login": current_user.get('login')})
                return {"msg": "You cannot delete admin"}, 403
            deleted = db.delete(record_id=user_id)
            if not deleted:
                logger.warning(f"Пользователь user_id={user_id} не найден при hard удалении",
                               extra={"login": current_user.get('login')})
                return {"msg": "User not found"}, 404
            logger.info(f"Пользователь user_id={user_id} удален окончательно",
                        extra={"login": current_user.get('login')})
            return {"msg": f"User {user_id} hard deleted successfully", "user_id": user_id}, 200
        except Exception as e:
            logger.error(f"Ошибка при окончательном удалении пользователя user_id={user_id}: {e}",
                         extra={"login": current_user.get('login')})
            return {'msg': f"Error during hard deleting user: {e}"}, 500


@user_ns.route('/<string:user_id>/edit')
class UserEdit(Resource):
    @jwt_required()
    @user_ns.expect(user_create_model)
    @user_ns.marshal_with(user_msg_model)
    @user_ns.response(400, "Bad request, invalid data.")
    @user_ns.response(404, "User not found")
    @user_ns.response(500, "Internal Server Error")
    def patch(self, user_id):
        current_user = json.loads(get_jwt_identity())
        if current_user['role'] != 'admin':
            logger.warning(f"Несанкционированный запрос на редактирование пользователя user_id={user_id}.",
                           extra={"login": current_user.get('login')}
                           )
            return {"msg": "Forbidden"}, 403
        logger.info(f"Запрос на редактирование пользователя user_id={user_id}",
                    extra={"login": current_user.get('login')})
        schema = UserEditSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        login = data.get("login")
        password = data.get("password")
        name = data.get("name")
        role = data.get("role")
        category = data.get("category")

        # Логируем входные данные для редактирования
        logger.debug(f"Параметры редактирования: login={login}, password={'*' if password else None}, name={name}, role={role}, category={category}",
                     extra={"login": current_user.get('login')})

        # Можно добавить базовую валидацию, если необходимо
        if not (login and name and role):
            logger.warning(f"Отсутствуют обязательные параметры для редактирования пользователя user_id={user_id}",
                           extra={"login": current_user.get('login')})
            return {"msg": "Bad request, invalid data."}, 400

        try:
            # Преобразуем строку в UUID
            try:
                user_id = UUID(user_id)
            except ValueError:
                return {"msg": "Invalid user ID format"}, 400
            from app.database.managers.user_manager import UserManager
            db = UserManager()
            logger.debug("Обновление данных пользователя в базе...",
                         extra={"login": current_user.get('login')})
            updated = db.update(record_id=user_id, login=login,
                                role=role, category=category, name=name)
            if not updated:
                logger.warning(f"Пользователь user_id={user_id} не найден при редактировании",
                               extra={"login": current_user.get('login')})
                return {"msg": "User not found"}, 404

            if password:
                logger.debug(f"Обновление пароля пользователя user_id={user_id}...",
                             extra={"login": current_user.get('login')})
                db.update_user_password(user_id, password)

            logger.info(f"Успешно отредактирован пользователь user_id={user_id}",
                        extra={"login": current_user.get('login')})
            return {"msg": "User edited successfully", "user_id": user_id}, 200
        except Exception as e:
            logger.error(f"Ошибка при редактировании пользователя user_id={user_id}: {e}",
                         extra={"login": current_user.get('login')})
            return {"msg": f"Error in editing user: {e}"}, 500


@user_ns.route('/all')
class UserAll(Resource):
    @jwt_required()
    @user_ns.expect(user_filter_parser)
    @user_ns.marshal_with(user_all_response)
    @user_ns.response(500, "Internal Server Error")
    def get(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Запрос на получение списка пользователей.",
                    extra={"login": current_user.get('login')})

        # Разбор аргументов через парсер
        # Валидация query-параметров через Marshmallow
        schema = UserFilterSchema()
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
            'login': args.get('login'),
            'name': args.get('name'),
            'role': args.get('role'),
            'category': args.get('category'),
            'deleted': args.get('deleted'),
            'created_by': args.get('created_by'),
            'created_at': args.get('created_at'),
        }

        # Логируем параметры фильтрации
        logger.debug(f"Параметры фильтрации: offset={offset}, limit={limit}, sort_by={sort_by}, sort_order={sort_order}, filters={filters}",
                     extra={"login": current_user.get('login')})

        try:
            from app.database.managers.user_manager import UserManager
            db = UserManager()
            logger.debug("Получение списка пользователей из базы...",
                         extra={"login": current_user.get('login')})
            users = db.get_all_filtered(
                offset, limit, sort_by, sort_order, **filters)
            logger.info(f"Успешно получен список пользователей: количество={len(users)}",
                        extra={"login": current_user.get('login')})
            return {"users": users, "msg": "Users found successfully"}, 200
        except Exception as e:
            logger.error(f"Ошибка при получении списка пользователей: {e}",
                         extra={"login": current_user.get('login')})
            return {'msg': f"Error during getting users: {e}"}, 500
