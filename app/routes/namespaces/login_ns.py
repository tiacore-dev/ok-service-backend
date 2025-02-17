import json
import logging
from flask import request, jsonify
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from flask_jwt_extended import create_access_token, create_refresh_token
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.routes.models.login_models import login_model
from app.routes.models.login_models import refresh_model, response_auth
from app.schemas.login_schemas import LoginSchema, RefreshTokenSchema

logger = logging.getLogger('ok_service')

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
        db = UserManager()
        schema = LoginSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        login = data.get("login", None)
        password = str(data.get("password", None))

        logger.info("Login attempt", extra={"login": login})

        if not (db.exists(login=login) and db.check_password_db(login, password)):
            logger.warning("Authentication failed: bad username or password",
                           extra={"login": login})
            return {"msg": "Bad username or password"}, 401

        user = db.filter_one_by_dict(login=login)
        if not user:
            logger.error("User not found", extra={"login": login})
            return {"msg": "User not found"}, 404
        identity = json.dumps({
            "user_id": user['user_id'],
            "role": user['role'],
            "login": login
        })
        access_token = create_access_token(identity=identity)
        refresh_token = create_refresh_token(identity=identity)

        logger.info("Authentication successful", extra={"login": login})
        return {"access_token": access_token, "refresh_token": refresh_token,
                "msg": "Authentication successful", "user_id": user['user_id']}, 200


@login_ns.route('/refresh')
class AuthRefresh(Resource):
    @login_ns.expect(refresh_model)
    @login_ns.marshal_with(response_auth)
    def post(self):
        schema = RefreshTokenSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        refresh_token = data.get('refresh_token', None)
        logger.debug("Refresh token request received",
                     extra={"refresh_token": refresh_token})

        if not refresh_token:
            logger.error("Missing refresh token in request")
            return jsonify({"msg": "Missing refresh token"}), 400

        try:
            verify_jwt_in_request(refresh=True, locations=["json"])
            logger.debug("Refresh token verified successfully")
        except Exception as e:
            logger.error(f"Refresh token verification failed: {str(e)}",
                         extra={"refresh_token": refresh_token})
            return jsonify({"msg": str(e)}), 401

        current_user = get_jwt_identity()
        logger.debug("Generating new access and refresh tokens",
                     extra={"user": current_user})
        new_access_token = create_access_token(identity=current_user)
        new_refresh_token = create_refresh_token(identity=current_user)

        logger.info("Tokens refreshed successfully",
                    extra={"user": current_user})
        return {"access_token": new_access_token, "refresh_token": new_refresh_token,
                "msg": "Token refreshed successfully"}, 200
