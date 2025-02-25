from flask_restx import fields,  Model,  reqparse
from app.utils.helpers import generate_swagger_model
from app.schemas.subscription_schemas import SubscriptionSchema

# Определяем модель, которая описывает входные данные
subscription_create_model = generate_swagger_model(
    SubscriptionSchema(), 'SubscriptionCreate'
)

subscription_msg_model = Model('SubscriptionMessage', {
    'msg': fields.String(description='Response message'),
    "subscription_id": fields.String(description='ID of subscription')
})

notification_model = Model('Notification', {
    "subscription_id": fields.String(required=True, description='Subscription ID'),
    "message": fields.String(required=True, description='Message that you want to send in web-push')
})

subscription_model = Model('SubscriptionModel', {
    "subscription_id": fields.String(required=True, description='Subscription ID'),
    "user": fields.String(required=True, description='Subscription ID'),
    "endpoint": fields.String(required=True, description='Subscription ID'),
    "keys": fields.String(required=True, description='Subscription ID')
})


subscription_all_response = Model('SubscriptionAllResponse', {
    'msg': fields.String(description='Response message'),
    'subscriptions': fields.List(fields.Nested(subscription_model), description='List of subscriptions')
})

subscription_filter_parser = reqparse.RequestParser()
subscription_filter_parser.add_argument(
    'offset', type=int, required=False, default=0, help='Offset for pagination')
subscription_filter_parser.add_argument(
    'limit', type=int, required=False, default=10, help='Limit for pagination')
subscription_filter_parser.add_argument(
    'sort_by', type=str, required=False, help='Field for sorting')
subscription_filter_parser.add_argument(
    'sort_order', type=str, required=False, choices=['asc', 'desc'], help='Sorting order')
subscription_filter_parser.add_argument(
    'user', type=str, required=False, help='Filter by user')
subscription_filter_parser.add_argument(
    'endpoint', type=str, required=False, help='Filter by endpoint')
subscription_filter_parser.add_argument(
    'keys', type=str, required=False, help='Filter by keys')
