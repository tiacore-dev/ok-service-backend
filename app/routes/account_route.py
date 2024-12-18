"""
Модуль для работы с роутами, связанными с аккаунтом
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import json
# Получаем логгер по его имени
logger = logging.getLogger('ok_service')

account_bp = Blueprint('account', __name__)


@account_bp.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    try:
        current_user = get_jwt_identity()
        current_user = json.loads(current_user)
        logger.info(f"Пользователь авторизован: {current_user['user_id']}",
                    extra={'login': current_user['login']}
                    )
        return jsonify({"message": "Access granted"}), 200
    except Exception as e:
        logger.error(f"Ошибка авторизации: {str(e)}")
        return jsonify({"error": "Authorization failed"}), 401


@account_bp.route('/get_username', methods=['GET'])
@jwt_required()  # Требуется авторизация с JWT
def get_username():
    current_user = get_jwt_identity()
    logger.info(f"Получено имя пользователя: {current_user}")
    return jsonify(current_user), 200
