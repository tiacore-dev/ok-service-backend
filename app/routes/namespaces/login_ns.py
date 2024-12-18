from flask import request, jsonify
from flask_restx import Namespace, Resource
from flask_jwt_extended import create_access_token, create_refresh_token
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
import json
from app.routes.models.login_models import login_model
from app.routes.models.login_models import refresh_model, response_auth

login_ns = Namespace('auth', description='Authentication related operations')


login_ns.models[login_model.name] = login_model
login_ns.models[refresh_model.name] = refresh_model
login_ns.models[response_auth.name] = response_auth


@login_ns.route('/login')
class AuthLogin(Resource):
    @login_ns.expect(login_model)
    @login_ns.marshal_with(response_auth)
    def post(self):
        from app.database.managers.user_manager import UserManager
        # Создаем экземпляр менеджера базы данных
        db = UserManager()
        login = request.json.get("login", None)
        password = request.json.get("password", None)

        # Проверяем пользователя в базе данных
        if not (db.exists(login=login) and db.check_password(login, password)):
            return {"msg": "Bad username or password"}, 401

        user = db.filter_one_by_dict(login=login)
        identity = json.dumps({
            "user_id": user['user_id'],
            "role": user['role']['role_id'],
            "login": login
        })
        # Генерируем Access и Refresh токены с дополнительной информацией
        access_token = create_access_token(identity=identity)
        refresh_token = create_refresh_token(identity=identity)

        return {"access_token": access_token,
                "refresh_token": refresh_token}, 200


@login_ns.route('/refresh')
class AuthRefresh(Resource):
    # Использование модели для валидации запроса
    @login_ns.expect(refresh_model)
    @login_ns.marshal_with(response_auth)
    def post(self):
        # Получение токена из тела запроса
        refresh_token = request.json.get('refresh_token', None)

        if not refresh_token:
            return jsonify({"msg": "Missing refresh token"}), 400

        try:
            # Явная валидация токена
            verify_jwt_in_request(refresh=True, locations=["json"])
        except Exception as e:
            return jsonify({"msg": str(e)}), 401

        # Получение текущего пользователя
        current_user = get_jwt_identity()

        # Генерация нового access токена
        new_access_token = create_access_token(identity=current_user)
        new_refresh_token = create_refresh_token(identity=current_user)
        return {"access_token": new_access_token,
                "refresh_token": new_refresh_token
                }, 200
