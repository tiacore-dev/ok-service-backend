import logging
import json
from uuid import UUID
from base64 import urlsafe_b64encode
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key, PublicFormat, Encoding
from flask import request
from pywebpush import webpush, WebPushException
from marshmallow import ValidationError
from app.schemas.subscription_schemas import SubscriptionSchema, SubscriptionGetSchema
from app.routes.models.subscription_models import (
    subscription_all_response, subscription_create_model,
    subscription_model, subscription_msg_model,
    subscription_filter_parser, notification_model
)


subscription_ns = Namespace(
    'subscriptions', description='Subscription actions')

subscription_ns.models[subscription_create_model.name] = subscription_create_model
subscription_ns.models[subscription_msg_model.name] = subscription_msg_model
subscription_ns.models[subscription_all_response.name] = subscription_all_response
subscription_ns.models[subscription_model.name] = subscription_model
subscription_ns.models[notification_model.name] = notification_model

logger = logging.getLogger('ok_service')

# Чтение публичного ключа из файла
with open("vapid_public_key.pem", "rb") as f:
    public_key = load_pem_public_key(f.read())

# Чтение приватного ключа из файла
with open("vapid_private_key.pem", "rb") as f:
    private_key = load_pem_private_key(f.read(), password=None)

# Извлечение сырого публичного ключа
raw_public_key = public_key.public_bytes(
    encoding=Encoding.X962,
    format=PublicFormat.UncompressedPoint
)

# Преобразование в Base64 URL-safe
VAPID_PUBLIC_KEY = urlsafe_b64encode(raw_public_key).decode('utf-8')

VAPID_CLAIMS = {
    "sub": "https://fcm.googleapis.com"
}


subscription_ns.models[subscription_create_model.name] = subscription_create_model


@subscription_ns.route('/subscribe')
class Subscribe(Resource):
    @jwt_required()
    @subscription_ns.expect(subscription_create_model)
    @subscription_ns.marshal_with(subscription_msg_model)
    def post(self):
        from app.database.managers.subscription_manager import SubscriptionsManager

        db = SubscriptionsManager()
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Полученные данные: {request.json}")

        # Используем правильную схему
        schema = SubscriptionSchema()
        try:
            # Загружаем и валидируем данные
            data = schema.load(request.json)
        except ValidationError as err:
            logger.error(f"Ошибка валидации данных: {err.messages}")
            return {"error": err.messages}, 400

        # Преобразуем объект в JSON-строку перед сохранением
        endpoint = data['endpoint']
        keys = json.dumps(data['keys'])
        # Проверяем, существует ли подписка
        if db.exists(endpoint=endpoint):
            subscription = db.filter_one_by_dict(
                user=current_user['user_id'])
            if subscription:
                # logger.info(f"Информация о существующей подписке: {subscription}")
                db.update(
                    record_id=subscription['subscription_id'], keys=keys)
                return {"message": "Subscription already exists.", "subscription_id": subscription['subscription_id']}, 200
            return {"message": "Subscription already exists."}, 201

        # Сохраняем подписку
        subscription = db.add(endpoint=endpoint, keys=keys,
                              user=current_user['user_id'])

        return {"message": "Subscription added.", "subscription_id": subscription['subscription_id']}, 201


@subscription_ns.route('/send_notification')
class SendNotification(Resource):
    @jwt_required()
    @subscription_ns.expect(notification_model)
    @subscription_ns.marshal_with(subscription_msg_model)
    def post(self):
        from app.database.managers.subscription_manager import SubscriptionsManager
        db = SubscriptionsManager()
        message = request.json.get('message', 'Test notification')
        subscription_id = request.json.get('subscription_id')

        if not subscription_id:
            logger.warning("No subscription_id provided.")
            return {"message": "No subscription ID provided."}, 400
        subscription_id = UUID(subscription_id)
        subscription = db.get_by_id(subscription_id)
        if not subscription:
            logger.warning(f"No subscription found for ID: {subscription_id}")
            return {"message": "Subscription not found."}, 404
        subscription_info = {
            "endpoint": subscription['endpoint'], "keys": json.loads(subscription['keys'])}

        try:
            message_data = {'header': 'Test Notification', 'text': message}
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(message_data),
                vapid_private_key=urlsafe_b64encode(
                    private_key.private_numbers().private_value.to_bytes(
                        length=(private_key.key_size + 7) // 8,
                        byteorder="big"
                    )
                ).decode('utf-8'),
                vapid_claims=VAPID_CLAIMS
            )
            logger.info(f"""Notification sent to subscription ID: {
                subscription_id}""")
            return {"message": "Notification sent successfully."}, 200
        except WebPushException as ex:
            logger.error(f"Failed to send notification: {str(ex)}")
            return {"error": "Failed to send notification."}, 500


@subscription_ns.route('/<string:subscription_id>/unsubscribe')
class Unsubscribe(Resource):
    @jwt_required()
    @subscription_ns.marshal_with(subscription_msg_model)
    def delete(self, subscription_id):
        from app.database.managers.subscription_manager import SubscriptionsManager
        db = SubscriptionsManager()

        if not subscription_id:
            logger.warning("Unsubscribe request missing 'subscription_id'")
            return {"error": "Missing 'subscription_id' in request data"}, 400
        subscription_id = UUID(subscription_id)
        # Удаляем подписку
        if not db.delete(subscription_id):
            logger.info(f"No subscription found for ID: {subscription_id}")
            return {"message": "Subscription not found."}, 404

        logger.info(f"Subscription removed: {subscription_id}")
        return {"message": "Subscription removed successfully."}, 200


@subscription_ns.route('/all')
class GetAllSubscriptions(Resource):
    @jwt_required()
    @subscription_ns.expect(subscription_filter_parser)
    @subscription_ns.marshal_with(subscription_all_response)
    def get(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to fetch all shift reports",
                    extra={"login": current_user})

        # Валидация query-параметров через Marshmallow
        schema = SubscriptionGetSchema()
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
            'user': args.get('user') if args.get('user') else None,
            'endpoint': args.get('endpoint', None),
            'keys': args.get('keys', None)
        }
        logger.debug(f"Fetching subscriptions with filters: {filters}, offset={offset}, limit={limit}",
                     extra={"login": current_user})

        try:
            from app.database.managers.subscription_manager import SubscriptionsManager
            db = SubscriptionsManager()
            subscriptions = db.get_all_filtered(
                offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order, **filters)
            logger.info(f"Successfully fetched {len(subscriptions)} subscriptions",
                        extra={"login": current_user})
            return {"msg": "Subscriptions found successfully", "subscriptions": subscriptions}, 200
        except Exception as e:
            logger.error(f"Error fetching subscriptions: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error fetching subscriptions: {e}"}, 500
