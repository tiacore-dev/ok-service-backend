import logging
import json
from uuid import UUID
from base64 import urlsafe_b64encode
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key, PublicFormat, Encoding
from flask import request
from pywebpush import webpush, WebPushException
from marshmallow import ValidationError
from app.schemas.shift_report_schemas import ShiftReportCreateSchema

subscription_ns = Namespace(
    'subscriptions', description='Subscription actions')

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

# Определяем модель, которая описывает входные данные
subscription_create_model = subscription_ns.model('SubscriptionCreate', {
    'subscription_info': fields.String(required=True, description='Subscription info in raw text')
})

subscription_msg_model = subscription_ns.model('SubscriptionMessage', {
    'msg': fields.String(description='Response message')
})

notification_model = subscription_ns.model('Notification', {
    "subscription_id": fields.String(required=True, description='Subscription ID'),
    "message": fields.String(required=True, description='Message that you want to send in web-push')
})


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
        # Получаем "сырые" данные из тела запроса
        schema = ShiftReportCreateSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)
        except ValidationError as err:
            # Возвращаем 400 с описанием ошибки
            return {"error": err.messages}, 400
        subscription_info = data.get('transcription_info')
        # Проверяем существование подписки
        if db.exists(subscription_data=subscription_info):
            return {"message": "Subscription already exists."}, 200

        # Добавляем подписку
        db.add(subscription_data=subscription_info,
               user=current_user['user_id'])
        return {"message": "Subscription added."}, 201


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

        subscription = db.get_by_id(subscription_id)
        if not subscription:
            logger.warning(f"No subscription found for ID: {subscription_id}")
            return {"message": "Subscription not found."}, 404
        subscription_info = json.loads(subscription['subscription_data'])

        try:
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(
                    {"title": "Test Notification", "body": message}),
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
