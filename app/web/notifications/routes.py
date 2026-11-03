"""Session-bound notification and device APIs."""
from functools import wraps
from typing import TypedDict
from uuid import UUID

from flask import current_app, g, request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError

from app.adapters.notifications import SQLAlchemyNotificationRepository
from app.adapters.push_subscriptions import SQLAlchemyPushSubscriptionRepository
from app.database import db_globals
from app.database.models import Users
from app.decorators.api_key_or_jwt_required import api_key_or_jwt_required
from app.use_cases.notifications import (
    CountUnviewedNotificationsUseCase, ListNotificationHistoryUseCase,
    MarkNotificationViewedUseCase,
)
from app.use_cases.push_subscriptions import ListPushSubscriptions, RevokePushSubscription
from app.web.notifications.schemas import NotificationItemSchema, NotificationListQuerySchema

notification_ns = Namespace("notifications", description="Personal and administrative notifications")


def secured(fn):
    # API keys provide an additional route permission, never a user identity.
    @wraps(fn)
    @jwt_required()
    def wrapped(*args, **kwargs):
        if "API-Key" in request.headers:
            if not request.headers.get("API-Key"):
                return {"msg": "Invalid API key"}, 403
            check = api_key_or_jwt_required(lambda: None)()
            if check is not None:
                return check
        return fn(*args, **kwargs)
    return wrapped


def current_user():
    return UUID(str(g.jwt_current_user["user_id"]))


class PageParams(TypedDict):
    offset: int
    limit: int


def page() -> PageParams:
    loaded = NotificationListQuerySchema().load(request.args.to_dict())
    if not isinstance(loaded, dict):
        raise RuntimeError("Invalid pagination schema result")
    offset, limit = loaded.get("offset"), loaded.get("limit")
    if not isinstance(offset, int) or not isinstance(limit, int):
        raise RuntimeError("Invalid pagination schema result")
    return {"offset": offset, "limit": limit}


def admin_target(user_id):
    if g.jwt_current_user.get("role") != "admin":
        return {"msg": "Forbidden"}, 403
    factory = db_globals.Session
    if factory is None:
        raise RuntimeError("Database session is not initialized")
    with factory() as session:
        user = session.get(Users, user_id)
        if user is None or user.deleted:
            return {"msg": "User not found"}, 404
    return None


def list_history(user_id):
    try:
        params = page()
    except ValidationError as error:
        return {"error": error.messages}, 400
    items = ListNotificationHistoryUseCase(SQLAlchemyNotificationRepository()).execute(user_id, **params)
    return {"items": NotificationItemSchema(many=True).dump(items), **params}, 200


def list_devices(user_id):
    try:
        params = page()
    except ValidationError as error:
        return {"error": error.messages}, 400
    items = ListPushSubscriptions(SQLAlchemyPushSubscriptionRepository()).execute(user_id, **params)
    return {"items": [{"subscription_id": str(item.subscription_id), "platform": item.platform,
                       "active": item.active, "created_at": item.created_at,
                       "updated_at": item.updated_at, "revoked_at": item.revoked_at}
                      for item in items], **params}, 200


@notification_ns.route("")
class NotificationHistory(Resource):
    @secured
    def get(self):
        return list_history(current_user())


@notification_ns.route("/unread-count")
class UnreadCount(Resource):
    @secured
    def get(self):
        return {"count": CountUnviewedNotificationsUseCase(SQLAlchemyNotificationRepository()).execute(current_user())}, 200


@notification_ns.route("/<uuid:notification_id>/view")
class NotificationViewed(Resource):
    @secured
    def post(self, notification_id):
        try:
            browser_id = UUID(str(request.cookies.get(current_app.config["BROWSER_ID_COOKIE_NAME"])))
        except (TypeError, ValueError):
            return {"msg": "Browser identity is required"}, 401
        item = MarkNotificationViewedUseCase(SQLAlchemyNotificationRepository()).execute(notification_id, current_user(), browser_id)
        if item is None:
            return {"msg": "Notification not found"}, 404
        return {"notification_id": str(item.notification_id), "viewed": item.viewed, "viewed_at": item.viewed_at}, 200


@notification_ns.route("/push/subscriptions")
class Devices(Resource):
    @secured
    def get(self):
        return list_devices(current_user())


@notification_ns.route("/push/subscriptions/<uuid:subscription_id>")
class Device(Resource):
    @secured
    def delete(self, subscription_id):
        item = RevokePushSubscription(SQLAlchemyPushSubscriptionRepository()).execute(subscription_id, current_user())
        return ({"msg": "Subscription not found"}, 404) if item is None else ("", 204)


@notification_ns.route("/admin/users/<uuid:user_id>")
class AdminHistory(Resource):
    @secured
    def get(self, user_id):
        error = admin_target(user_id)
        return error if error else list_history(user_id)


@notification_ns.route("/admin/users/<uuid:user_id>/push/subscriptions")
class AdminDevices(Resource):
    @secured
    def get(self, user_id):
        error = admin_target(user_id)
        return error if error else list_devices(user_id)
