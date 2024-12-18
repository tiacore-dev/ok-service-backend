from flask import request, jsonify
from flask_restx import Namespace, Resource
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, verify_jwt_in_request
from flask_cors import cross_origin
import json

from app.routes.models.login_models import login_model, refresh_model, response_auth

login_ns = Namespace('auth', description='Authentication related operations')


login_ns.models[login_model.name] = login_model
login_ns.models[refresh_model.name] = refresh_model
login_ns.models[response_auth.name] = response_auth


@login_ns.route('/')
class Auth(Resource):
    @cross_origin()
    @login_ns.expect(login_model)
    @login_ns.marshal_with(response_auth)
    def post(self):
        from app.database.managers.user_manager import UserManager
        # Создаем экземпляр менеджера базы данных
        db = UserManager()
        login = request.json.get("login", None)
        password = request.json.get("password", None)

        # Проверяем пользователя в базе данных
        if not db.exists(login=login) or not db.check_password(login, password):
            return {"msg": "Bad username or password"}, 401
        
        user = db.filter_one_by_dict(login=login)
        identity = json.dumps({
            "user_id": user['user_id'],
            "role": user['role']['role_id']
        })
        # Генерируем Access и Refresh токены с дополнительной информацией
        access_token = create_access_token(identity=identity)
        refresh_token = create_refresh_token(identity=identity)

        return jsonify(access_token=access_token, refresh_token=refresh_token), 200

@login_ns.route('/refresh')
class Auth(Resource):
    @cross_origin()
    @login_ns.expect(refresh_model)  # Использование модели для валидации запроса
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
        new_refresh_token = create_refresh_token(identity = current_user)
        return {"access_token": new_access_token,
                        "refresh_token": new_refresh_token
                        }, 200
