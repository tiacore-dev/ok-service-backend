from __future__ import annotations

import json
from typing import TypedDict, cast
from uuid import UUID

from flask import current_app, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource, fields
from marshmallow import ValidationError

from app.adapters.push_subscriptions import SQLAlchemyPushSubscriptionRepository
from app.domain.push_subscriptions import PushSubscriptionValidationError
from app.schemas.push_subscription_schemas import PushSubscriptionSchema
from app.use_cases.push_subscriptions import RegisterPushSubscription
from app.web._typing import to_plain_dict


push_subscription_ns = Namespace(
    "notifications/push", description="Current browser push subscription"
)

subscription_model = push_subscription_ns.model(
    "PushSubscription",
    {
        "platform": fields.String(required=True, enum=["web"]),
        "token": fields.String(required=True, description="FCM token"),
    },
)


class PushSubscriptionPayload(TypedDict):
    platform: str
    token: str


def _jwt_subject() -> tuple[UUID, UUID] | None:
    try:
        claims = get_jwt()
        session_id = UUID(str(claims["session_id"]))
        identity = get_jwt_identity()
        payload = json.loads(identity) if isinstance(identity, str) else identity
        return session_id, UUID(str(payload["user_id"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


@push_subscription_ns.route("/subscription")
class CurrentBrowserPushSubscription(Resource):
    @push_subscription_ns.expect(subscription_model)
    @push_subscription_ns.doc(
        responses={401: "JWT session or browser binding is invalid", 503: "Storage unavailable"}
    )
    @jwt_required()
    def put(self):
        subject = _jwt_subject()
        raw_browser_id = request.cookies.get(current_app.config["BROWSER_ID_COOKIE_NAME"])
        try:
            browser_id = UUID(str(raw_browser_id))
        except (TypeError, ValueError):
            # Do not generate a replacement here: it would not be bound to the
            # already-issued authorization session and must not affect a row.
            return {"msg": "Browser identity is required"}, 401
        if subject is None:
            return {"msg": "JWT session is invalid"}, 401
        try:
            data = cast(
                PushSubscriptionPayload,
                PushSubscriptionSchema().load(
                    to_plain_dict(request.get_json(silent=True), "Request body is required")
                ),
            )
            subscription = RegisterPushSubscription(
                SQLAlchemyPushSubscriptionRepository()
            ).execute(subject[1], browser_id, subject[0], data["platform"], data["token"])
        except ValidationError as error:
            return {"error": error.messages}, 400
        except ValueError as error:
            return {"msg": str(error)}, 400
        except PermissionError:
            return {"msg": "JWT session is invalid"}, 401
        except Exception:
            return {"msg": "Push subscription unavailable"}, 503
        return {
            "subscription_id": str(subscription.subscription_id),
            "platform": subscription.platform,
            "active": subscription.active,
            "created_at": subscription.created_at,
            "updated_at": subscription.updated_at,
        }, 200
