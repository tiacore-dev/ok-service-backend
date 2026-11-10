"""Session-bound notification and device APIs."""
from functools import wraps
from typing import TypedDict
from uuid import UUID

from flask import current_app, g, request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError

from app.adapters.notifications import SQLAlchemyNotificationRepository
from app.adapters.notifications.bulk_repository import BulkNotificationRepository
from app.adapters.push_subscriptions import SQLAlchemyPushSubscriptionRepository
from app.database import db_globals
from app.database.models import Users
from app.decorators.api_key_or_jwt_required import api_key_or_jwt_required
from app.use_cases.notifications import (
    CountUnviewedNotificationsUseCase, ListNotificationHistoryUseCase,
    MarkNotificationViewedUseCase,
)
from app.use_cases.push_subscriptions import ListPushSubscriptions, RevokePushSubscription
from app.web.notifications.schemas import BulkNotificationSchema, NotificationItemSchema, NotificationListQuerySchema
from app.domain.notifications import NotificationIdempotencyConflictError, NotificationValidationError
from app.use_cases.notifications.bulk import BulkForbiddenError, BulkRecipientsError, BulkNotificationUseCase

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


class BulkParams(TypedDict):
    recipient_user_ids: list[UUID]
    title: str
    text: str
    link: str | None
    idempotency_key: str


def bulk_params() -> BulkParams:
    loaded = BulkNotificationSchema().load(request.get_json(silent=True) or {})
    if not isinstance(loaded, dict):
        raise RuntimeError("Invalid bulk notification schema result")
    recipients = loaded.get("recipient_user_ids")
    title, text = loaded.get("title"), loaded.get("text")
    link, key = loaded.get("link"), loaded.get("idempotency_key")
    if (not isinstance(recipients, list)
            or not all(isinstance(item, UUID) for item in recipients)
            or not isinstance(title, str) or not isinstance(text, str)
            or (link is not None and not isinstance(link, str))
            or not isinstance(key, str)):
        raise RuntimeError("Invalid bulk notification schema result")
    return {"recipient_user_ids": recipients, "title": title, "text": text,
            "link": link, "idempotency_key": key}


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


@notification_ns.route("/admin/bulk")
class AdminBulk(Resource):
    @secured
    def post(self):
        if g.jwt_current_user.get("role") != "admin":
            return {"msg": "Forbidden"}, 403
        try:
            data = bulk_params()
            actor_id = current_user()
            repository = BulkNotificationRepository(actor_id)
            result = BulkNotificationUseCase(repository).execute(
                actor_id, tuple(data["recipient_user_ids"]), data["title"], data["text"],
                data["link"], data["idempotency_key"]
            )
            return {"notification_id": str(result.notification_id),
                    "recipient_count": len(data["recipient_user_ids"]),
                    "created_at": result.created_at, "replayed": repository.was_replay}, (200 if repository.was_replay else 201)
        except ValidationError as error:
            return {"error": error.messages}, 400
        except NotificationValidationError as error:
            return {"msg": str(error)}, 400
        except BulkForbiddenError:
            return {"msg": "Forbidden"}, 403
        except BulkRecipientsError:
            return {"msg": "One or more recipients are unavailable"}, 400
        except NotificationIdempotencyConflictError:
            return {"msg": "Idempotency key conflict"}, 409
        except Exception:
            current_app.logger.exception("Bulk notification creation failed")
            return {"msg": "Internal server error"}, 500


@notification_ns.route("/admin/users/<uuid:user_id>/push/subscriptions")
class AdminDevices(Resource):
    @secured
    def get(self, user_id):
        error = admin_target(user_id)
        return error if error else list_devices(user_id)
