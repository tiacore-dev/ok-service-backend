from __future__ import annotations

import json
import logging
from base64 import urlsafe_b64encode
from pathlib import Path
from typing import Any, TypedDict, cast
from uuid import UUID

from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
)
from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError

from app.database.managers.subscription_manager import SubscriptionsManager
from app.web._typing import to_plain_dict

from .models import (
    notification_model,
    subscription_all_response,
    subscription_create_model,
    subscription_filter_parser,
    subscription_model,
    subscription_msg_model,
)
from app.schemas.subscription_schemas import SubscriptionGetSchema, SubscriptionSchema

try:
    from pywebpush import webpush
except ImportError:  # pragma: no cover - optional dependency fallback
    def webpush(*args: Any, **kwargs: Any) -> Any:  # type: ignore[no-redef]
        raise RuntimeError("pywebpush is not installed")

logger = logging.getLogger("ok_service")

subscription_ns = Namespace("subscriptions", description="Subscription actions")

subscription_ns.models[subscription_create_model.name] = subscription_create_model
subscription_ns.models[subscription_msg_model.name] = subscription_msg_model
subscription_ns.models[subscription_all_response.name] = subscription_all_response
subscription_ns.models[subscription_model.name] = subscription_model
subscription_ns.models[notification_model.name] = notification_model

VAPID_CLAIMS = {"sub": "https://fcm.googleapis.com"}


class SubscriptionPayload(TypedDict):
    endpoint: str
    keys: dict[str, Any]


def _get_current_user() -> dict[str, Any]:
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return identity
    if isinstance(identity, (str, bytes, bytearray)):
        try:
            parsed = json.loads(identity)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _vapid_private_key() -> str | None:
    private_key_path = Path(__file__).resolve().parents[3] / "vapid_private_key.pem"
    if not private_key_path.exists():
        return None

    with private_key_path.open("rb") as file_handle:
        private_key = cast(Any, load_pem_private_key(file_handle.read(), password=None))

    raw_private_key = private_key.private_numbers().private_value.to_bytes(
        length=(private_key.key_size + 7) // 8, byteorder="big"
    )
    return urlsafe_b64encode(raw_private_key).decode("utf-8")


@subscription_ns.route("/subscribe")
class Subscribe(Resource):
    @jwt_required()
    @subscription_ns.expect(subscription_create_model)
    @subscription_ns.marshal_with(subscription_msg_model)
    def post(self):
        current_user = _get_current_user()
        db = SubscriptionsManager()
        logger.info(f"Полученные данные: {request.json}", extra={"login": current_user})

        schema = SubscriptionSchema()
        try:
            raw_payload = to_plain_dict(
                request.get_json(silent=True), "Request body is required"
            )
            data = cast(SubscriptionPayload, schema.load(raw_payload))
        except ValidationError as err:
            logger.error(
                f"Ошибка валидации данных: {err.messages}",
                extra={"login": current_user},
            )
            return {"msg": "Invalid subscription data", "error": err.messages}, 400
        except ValueError as err:
            logger.error(f"Value error during subscription: {err}")
            return {"msg": str(err)}, 400

        endpoint = data["endpoint"]
        keys = json.dumps(data["keys"])

        if db.exists(endpoint=endpoint):
            subscription = db.filter_one_by_dict(user=current_user["user_id"])
            if subscription:
                db.update(record_id=subscription["subscription_id"], keys=keys)
                return {
                    "msg": "Subscription already exists.",
                    "subscription_id": subscription["subscription_id"],
                }, 200
            return {"msg": "Subscription already exists."}, 201

        subscription = db.add(endpoint=endpoint, keys=keys, user=current_user["user_id"])

        return {
            "msg": "Subscription added.",
            "subscription_id": subscription["subscription_id"],
        }, 201


@subscription_ns.route("/send_notification")
class SendNotification(Resource):
    @jwt_required()
    @subscription_ns.expect(notification_model)
    @subscription_ns.marshal_with(subscription_msg_model)
    def post(self):
        current_user = _get_current_user()
        db = SubscriptionsManager()
        raw_payload = request.get_json(silent=True) or {}
        message = raw_payload.get("message", "Test notification")
        subscription_id = raw_payload.get("subscription_id")

        if not subscription_id:
            logger.warning(
                "No subscription_id provided.", extra={"login": current_user}
            )
            return {"msg": "No subscription ID provided."}, 400

        try:
            subscription_uuid = UUID(str(subscription_id))
        except ValueError:
            return {"msg": "Invalid subscription ID format."}, 400

        subscription = db.get_by_id(subscription_uuid)
        if not subscription:
            logger.warning(
                f"No subscription found for ID: {subscription_uuid}",
                extra={"login": current_user},
            )
            return {"msg": "Subscription not found."}, 404

        vapid_private_key = _vapid_private_key()
        if not vapid_private_key:
            return {"msg": "Web push configuration is missing."}, 500

        subscription_info = {
            "endpoint": subscription["endpoint"],
            "keys": json.loads(subscription["keys"]),
        }

        try:
            message_data = {"header": "Test Notification", "text": message}
            cast(Any, webpush)(
                subscription_info=subscription_info,
                data=json.dumps(message_data),
                vapid_private_key=vapid_private_key,
                vapid_claims=VAPID_CLAIMS,
            )
            logger.info(
                f"Notification sent to subscription ID: {subscription_uuid}",
                extra={"login": current_user},
            )
            return {"msg": "Notification sent successfully."}, 200
        except Exception as ex:
            logger.error(
                f"Unexpected error while sending notification: {str(ex)}",
                extra={"login": current_user},
            )
            return {"msg": "Failed to send notification."}, 500


@subscription_ns.route("/<string:subscription_id>/unsubscribe")
class Unsubscribe(Resource):
    @jwt_required()
    @subscription_ns.marshal_with(subscription_msg_model)
    def delete(self, subscription_id):
        current_user = _get_current_user()
        db = SubscriptionsManager()

        if not subscription_id:
            logger.warning(
                "Unsubscribe request missing 'subscription_id'",
                extra={"login": current_user},
            )
            return {"msg": "Missing 'subscription_id' in request data"}, 400
        try:
            subscription_uuid = UUID(subscription_id)
        except ValueError:
            logger.warning(
                f"Invalid UUID format in unsubscribe request: {subscription_id}",
                extra={"login": current_user},
            )
            return {"msg": "Invalid subscription ID format."}, 400

        if not db.delete(subscription_uuid):
            logger.info(f"No subscription found for ID: {subscription_uuid}")
            return {"msg": "Subscription not found."}, 404

        logger.info(
            f"Subscription removed: {subscription_uuid}", extra={"login": current_user}
        )
        return {
            "msg": "Subscription removed successfully.",
            "subscription_id": str(subscription_uuid),
        }, 200


@subscription_ns.route("/all")
class GetAllSubscriptions(Resource):
    @jwt_required()
    @subscription_ns.expect(subscription_filter_parser)
    @subscription_ns.marshal_with(subscription_all_response)
    def get(self):
        current_user = _get_current_user()
        logger.info("Request to fetch all shift reports", extra={"login": current_user})

        schema = SubscriptionGetSchema()
        try:
            args = schema.load(request.args)
        except ValidationError as err:
            logger.error(
                f"Validation error: {err.messages}", extra={"login": current_user}
            )
            return {"msg": f"Invalid subscription filter: {err.messages}"}, 400

        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit", None)  # type: ignore
        sort_by = args.get("sort_by")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore
        filters = {
            "user": args.get("user") if args.get("user") else None,  # type: ignore
            "endpoint": args.get("endpoint", None),  # type: ignore
            "keys": args.get("keys", None),  # type: ignore
        }
        logger.debug(
            f"Fetching subscriptions with filters: {filters}, offset={offset}, limit={limit}",
            extra={"login": current_user},
        )

        try:
            db = SubscriptionsManager()
            subscriptions = db.get_all_filtered(
                offset=offset,
                limit=limit,
                sort_by=sort_by,  # type: ignore
                sort_order=sort_order,
                **filters,
            )
            logger.info(
                f"Successfully fetched {len(subscriptions)} subscriptions",
                extra={"login": current_user},
            )
            return {
                "msg": "Subscriptions found successfully",
                "subscriptions": subscriptions,
            }, 200
        except Exception as e:
            logger.error(
                f"Error fetching subscriptions: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error fetching subscriptions: {e}"}, 500
