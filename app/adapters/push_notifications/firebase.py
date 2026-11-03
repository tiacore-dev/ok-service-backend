from __future__ import annotations

import importlib
import logging
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Sequence

from app.domain.push_notifications import (
    PushDelivery,
    PushDeliveryStatus,
    PushNotification,
    PushTarget,
)
from app.use_cases.push_notifications import (
    PushProvider,
    PushProviderConfigurationError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FirebasePushProviderConfig:
    project_id: str
    credentials_path: str
    app_name: str = "ok-service-push"
    http_timeout_seconds: float = 10.0


class NoopPushProvider(PushProvider):
    """Explicitly disabled provider; it does not contact Firebase."""

    def send(
        self, notification: PushNotification, targets: Sequence[PushTarget]
    ) -> list[PushDelivery]:
        _ = notification
        return [
            PushDelivery(target.subscription_id, PushDeliveryStatus.DISABLED)
            for target in targets
        ]


class FirebasePushProvider(PushProvider):
    _app_lock = threading.Lock()

    def __init__(self, config: FirebasePushProviderConfig) -> None:
        if not config.project_id.strip():
            raise PushProviderConfigurationError("FCM_PROJECT_ID is required")
        if not config.credentials_path.strip():
            raise PushProviderConfigurationError(
                "GOOGLE_APPLICATION_CREDENTIALS is required"
            )
        self._config = config
        self._firebase_app: Any | None = None

    @staticmethod
    def _load_modules() -> tuple[Any, Any]:
        try:
            firebase_admin = importlib.import_module("firebase_admin")
            messaging = importlib.import_module("firebase_admin.messaging")
        except ImportError as exc:
            raise PushProviderConfigurationError(
                "firebase-admin is not installed"
            ) from exc
        return firebase_admin, messaging

    def _get_app(self) -> Any:
        if self._firebase_app is not None:
            return self._firebase_app
        firebase_admin, _ = self._load_modules()
        with self._app_lock:
            if self._firebase_app is not None:
                return self._firebase_app
            try:
                self._firebase_app = firebase_admin.get_app(self._config.app_name)
            except ValueError:
                try:
                    credential = firebase_admin.credentials.Certificate(
                        self._config.credentials_path
                    )
                    self._firebase_app = firebase_admin.initialize_app(
                        credential,
                        options={
                            "projectId": self._config.project_id,
                            "httpTimeout": self._config.http_timeout_seconds,
                        },
                        name=self._config.app_name,
                    )
                except Exception as exc:
                    raise PushProviderConfigurationError(
                        "Firebase credentials or application configuration is invalid"
                    ) from exc
        return self._firebase_app

    @staticmethod
    def _payload(notification: PushNotification) -> dict[str, str]:
        return {
            "notification_id": str(notification.notification_id),
            "title": notification.title,
            "body": notification.body,
            "route": notification.route,
        }

    @staticmethod
    def _error_name(exception: Exception | None) -> str:
        return type(exception).__name__ if exception is not None else "UnknownError"

    @staticmethod
    def _is_invalid_token(exception: Exception | None) -> bool:
        # UnregisteredError is Firebase Admin's affirmative token-invalid signal.
        # Do not deactivate on generic InvalidArgumentError: it can describe a
        # malformed message rather than a bad device token.
        return type(exception).__name__ == "UnregisteredError"

    @staticmethod
    def _is_configuration_error(exception: Exception | None) -> bool:
        return type(exception).__name__ in {
            "UnauthenticatedError",
            "PermissionDeniedError",
            "CredentialError",
        }

    @classmethod
    def _deliveries_for_global_failure(
        cls, targets: Sequence[PushTarget], exception: Exception
    ) -> list[PushDelivery]:
        status = (
            PushDeliveryStatus.CONFIGURATION_ERROR
            if cls._is_configuration_error(exception)
            else PushDeliveryStatus.TEMPORARY_FAILURE
        )
        error_code = cls._error_name(exception)
        logger.warning("Firebase push batch failed: %s", error_code)
        return [
            PushDelivery(target.subscription_id, status, error_code=error_code)
            for target in targets
        ]

    def send(
        self, notification: PushNotification, targets: Sequence[PushTarget]
    ) -> list[PushDelivery]:
        if not targets:
            return []
        try:
            _, messaging = self._load_modules()
            app = self._get_app()
        except PushProviderConfigurationError:
            raise

        payload = self._payload(notification)
        messages = [
            messaging.Message(
                token=target.token,
                data=payload,
                notification=messaging.Notification(
                    title=notification.title or None, body=notification.body or None
                ),
            )
            for target in targets
        ]
        try:
            response = messaging.send_each(messages, app=app)
        except Exception as exc:
            return self._deliveries_for_global_failure(targets, exc)

        deliveries: list[PushDelivery] = []
        for target, item in zip(targets, response.responses, strict=True):
            if getattr(item, "success", False):
                deliveries.append(
                    PushDelivery(
                        target.subscription_id,
                        PushDeliveryStatus.SENT,
                        provider_message_id=getattr(item, "message_id", None),
                    )
                )
                continue
            exception = getattr(item, "exception", None)
            status = (
                PushDeliveryStatus.INVALID_TOKEN
                if self._is_invalid_token(exception)
                else PushDeliveryStatus.CONFIGURATION_ERROR
                if self._is_configuration_error(exception)
                else PushDeliveryStatus.TEMPORARY_FAILURE
            )
            deliveries.append(
                PushDelivery(
                    target.subscription_id,
                    status,
                    error_code=self._error_name(exception),
                )
            )
        return deliveries


def build_push_provider(settings: Any) -> PushProvider:
    def setting(name: str) -> Any:
        return (
            settings.get(name)
            if isinstance(settings, Mapping)
            else getattr(settings, name, None)
        )

    provider_name = str(setting("PUSH_PROVIDER") or "").strip().lower()
    if provider_name == "noop":
        return NoopPushProvider()
    if provider_name != "fcm":
        raise PushProviderConfigurationError("Unsupported PUSH_PROVIDER")
    configured_lease = setting("PUSH_WORKER_LEASE_SECONDS")
    lease_seconds = float(60 if configured_lease is None else configured_lease)
    if lease_seconds <= 0:
        raise PushProviderConfigurationError(
            "PUSH_WORKER_LEASE_SECONDS must be positive"
        )
    return FirebasePushProvider(
        FirebasePushProviderConfig(
            project_id=str(setting("FCM_PROJECT_ID") or ""),
            credentials_path=str(setting("GOOGLE_APPLICATION_CREDENTIALS") or ""),
            http_timeout_seconds=min(10.0, lease_seconds / 3),
        )
    )
