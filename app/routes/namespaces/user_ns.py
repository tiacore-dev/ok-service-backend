import json
import logging
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required
from flask_jwt_extended import get_jwt_identity
from app.routes.models.user_models import user_create_model, user_msg_model
from app.routes.models.user_models import user_all_response, user_response
from app.routes.models.user_models import user_filter_parser, user_model
logger = logging.getLogger('ok_service')

user_ns = Namespace('user', description='Authentication related operations')

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
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Запрос на добавление нового пользователя.",
                    extra={"login": current_user['login']})
        login = request.json.get("login")
        password = request.json.get("password")
        name = request.json.get("name")
        role = request.json.get("role")
        category = request.json.get("category")
        if not (login and password and name and role):
            return {"msg": "Bad request, invalid data."}, 400
        try:
            from app.database.managers.user_manager import UserManager
        # Создаем экземпляр менеджера базы данных
            db = UserManager()
            user_id = db.add_user(login=login, password=password,
                                  role=role, category=category, name=name)
            logger.info("Успешно добавлен новый пользователь",
                        extra={"login": current_user['login']})
            return {"user_id": user_id, "msg": "New user added successfully"}, 200
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователь: {e}",
                         extra={"login": current_user['login']})
            return {"msg": f"Error in adding new user: {e}"}, 500


@user_ns.route('/<string:user_id>/view')
class UserView(Resource):
    @ jwt_required()
    @user_ns.marshal_with(user_response)
    def get(self, user_id):
        from app.database.managers.user_manager import UserManager
        # Создаем экземпляр менеджера базы данных
        db = UserManager()
        try:
            user = db.get_by_id(user_id)
            return {"user": user, "msg": "User found successfully"}, 200
        except Exception as e:
            return {'msg': f"Error during getting user: {e}"}, 500


@user_ns.route('/<string:user_id>/delete/soft')
class UserDeleteSoft(Resource):
    @ jwt_required()
    @user_ns.marshal_with(user_msg_model)
    def patch(self, user_id):
        from app.database.managers.user_manager import UserManager
        # Создаем экземпляр менеджера базы данных
        db = UserManager()
        try:
            db.update(record_id=user_id, deleted=True)
            return {"msg": f"User {user_id} soft deleted successfully"}, 200
        except Exception as e:
            return {'msg': f"Error during soft deleting user: {e}"}, 500


@user_ns.route('/<string:user_id>/delete/hard')
class UserDeleteHard(Resource):
    @ jwt_required()
    @user_ns.marshal_with(user_msg_model)
    def delete(self, user_id):
        from app.database.managers.user_manager import UserManager
        # Создаем экземпляр менеджера базы данных
        db = UserManager()
        try:
            db.delete(record_id=user_id)
            return {"msg": f"User {user_id} hard deleted successfully"}, 200
        except Exception as e:
            return {'msg': f"Error during hard deleting user: {e}"}, 500


@user_ns.route('/<string:user_id>/edit')
class UserEdit(Resource):
    @jwt_required()
    @user_ns.expect(user_create_model)
    @user_ns.marshal_with(user_msg_model)
    def patch(self, user_id):
        current_user = json.loads(get_jwt_identity())
        logger.info("Запрос на добавление нового пользователя.",
                    extra={"login": current_user['login']})
        login = request.json.get("login")
        password = request.json.get("password")
        name = request.json.get("name")
        role = request.json.get("role")
        category = request.json.get("category")
        try:
            from app.database.managers.user_manager import UserManager
            # Создаем экземпляр менеджера базы данных
            db = UserManager()
            db.update(record_id=user_id, login=login,
                      role=role, category=category, name=name)
            if password:
                db.update_user_password(user_id, password)
            logger.info(f"Успешно отредактирован пользователь {user_id}",
                        extra={"login": current_user['login']})
            return {"msg": "User edited successfully"}, 200
        except Exception as e:
            logger.error(f"Ошибка при редактировании пользователь: {e}",
                         extra={"login": current_user['login']})
            return {"msg": f"Error in editing user: {e}"}, 500


@user_ns.route('/all')
class UserAll(Resource):
    @ jwt_required()
    @user_ns.expect(user_filter_parser)
    @user_ns.marshal_with(user_all_response)
    def get(self):
        from app.database.managers.user_manager import UserManager
        # Создаем экземпляр менеджера базы данных
        db = UserManager()
        offset = request.args.get(
            'offset', default=0, type=int)  # По умолчанию 0
        limit = request.args.get(
            'limit', default=10, type=int)    # По умолчанию 10
        sort_by = request.args.get('sort_by', None)  # Поле для сортировки
        sort_order = request.args.get(
            'sort_order', 'asc')  # Порядок сортировки
        filters = {
            'login': request.args.get('login'),
            'name': request.args.get('name'),
            'role': request.args.get('role'),
            'category': request.args.get('category'),
            'deleted': request.args.get('deleted', type=bool),
        }
        try:
            users = db.get_all_filtered(
                offset, limit, sort_by, sort_order, **filters)
            return {"users": users, "msg": "User found successfully"}, 200
        except Exception as e:
            return {'msg': f"Error during getting user: {e}"}, 500
