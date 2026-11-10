from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import uuid4

import pytest
from flask import Flask

from app.adapters.push_notifications import (
    FirebasePushProvider,
    FirebasePushProviderConfig,
    NoopPushProvider,
    build_push_provider,
)
from app.domain.push_notifications import (
    PushDeliveryStatus,
    PushNotification,
    PushTarget,
)
from app.use_cases.push_notifications import PushProviderConfigurationError


class _Response:
    def __init__(self, success, message_id=None, exception=None):
        self.success = success
        self.message_id = message_id
        self.exception = exception


class _Notification:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _Message:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@dataclass
class _CapturedFirebaseCall:
    messages: list[_Message] | None = None
    app: object | None = None


class _Firebase:
    def __init__(self, certificate_error=None):
        self.apps = {}
        self.initialize_calls = []
        self.certificate_error = certificate_error
        self.credentials = SimpleNamespace(Certificate=self.certificate)

    def certificate(self, path):
        if self.certificate_error:
            raise self.certificate_error
        return ("credential", path)

    def get_app(self, name):
        if name not in self.apps:
            raise ValueError("missing app")
        return self.apps[name]

    def initialize_app(self, credential, options, name):
        app = SimpleNamespace(credential=credential, options=options, name=name)
        self.apps[name] = app
        self.initialize_calls.append(app)
        return app


def _provider(monkeypatch, responses=None, *, certificate_error=None, send_error=None):
    from app.adapters.push_notifications import firebase

    admin = _Firebase(certificate_error)
    captured = _CapturedFirebaseCall()

    def send_each(messages, app):
        captured.messages = messages
        captured.app = app
        if send_error:
            raise send_error
        return SimpleNamespace(responses=responses or [])

    messaging = SimpleNamespace(
        Message=_Message, Notification=_Notification, send_each=send_each
    )
    monkeypatch.setattr(
        firebase.importlib,
        "import_module",
        lambda name: admin if name == "firebase_admin" else messaging,
    )
    return (
        FirebasePushProvider(
            FirebasePushProviderConfig("ok-dev", "/app/secrets/firebase.json")
        ),
        admin,
        captured,
    )


def _notification():
    return PushNotification(uuid4(), "Title", "Body", "/notifications/42")


def _targets():
    return [PushTarget(uuid4(), "token-one"), PushTarget(uuid4(), "token-two")]


def test_firebase_provider_sends_each_token_and_reuses_named_app(monkeypatch):
    provider, admin, captured = _provider(
        monkeypatch, [_Response(True, "message-one"), _Response(True, "message-two")]
    )
    targets = _targets()

    first = provider.send(_notification(), targets)
    second = provider.send(_notification(), targets)

    assert [delivery.status for delivery in first] == [
        PushDeliveryStatus.SENT,
        PushDeliveryStatus.SENT,
    ]
    assert [delivery.provider_message_id for delivery in second] == [
        "message-one",
        "message-two",
    ]
    assert len(admin.initialize_calls) == 1
    assert isinstance(captured.app, SimpleNamespace)
    assert captured.app is admin.initialize_calls[0]
    assert captured.app.options["httpTimeout"] == 10.0


def test_firebase_provider_builds_minimal_safe_payload(monkeypatch):
    provider, _, captured = _provider(monkeypatch, [_Response(True, "message")])
    notification = _notification()

    provider.send(notification, [_targets()[0]])

    assert captured.messages is not None
    message = captured.messages[0]
    assert message.kwargs["data"] == {
        "notification_id": str(notification.notification_id),
        "title": "Title",
        "body": "Body",
        "route": "/notifications/42",
    }
    assert message.kwargs["notification"].kwargs == {"title": "Title", "body": "Body"}
    assert message.kwargs["token"] == "token-one"


def test_firebase_provider_returns_per_token_partial_results(monkeypatch):
    TemporaryError = type("UnavailableError", (Exception,), {})
    provider, _, _ = _provider(
        monkeypatch,
        [_Response(True, "message"), _Response(False, exception=TemporaryError())],
    )
    targets = _targets()

    deliveries = provider.send(_notification(), targets)

    assert [
        (item.subscription_id, item.status, item.error_code) for item in deliveries
    ] == [
        (targets[0].subscription_id, PushDeliveryStatus.SENT, None),
        (targets[1].subscription_id, PushDeliveryStatus.TEMPORARY_FAILURE, "UnavailableError"),
    ]


def test_firebase_provider_marks_only_confirmed_invalid_token(monkeypatch):
    UnregisteredError = type("UnregisteredError", (Exception,), {})
    InvalidArgumentError = type("InvalidArgumentError", (Exception,), {})
    provider, _, _ = _provider(
        monkeypatch,
        [
            _Response(False, exception=UnregisteredError()),
            _Response(False, exception=InvalidArgumentError()),
        ],
    )

    deliveries = provider.send(_notification(), _targets())

    assert [item.status for item in deliveries] == [
        PushDeliveryStatus.INVALID_TOKEN,
        PushDeliveryStatus.TEMPORARY_FAILURE,
    ]


def test_firebase_authentication_error_is_reported_per_token_without_tokens_in_log(
    monkeypatch, caplog
):
    UnauthenticatedError = type("UnauthenticatedError", (Exception,), {})
    provider, _, _ = _provider(
        monkeypatch, send_error=UnauthenticatedError("credentials rejected")
    )

    deliveries = provider.send(_notification(), _targets())

    assert [item.status for item in deliveries] == [
        PushDeliveryStatus.CONFIGURATION_ERROR,
        PushDeliveryStatus.CONFIGURATION_ERROR,
    ]
    assert "UnauthenticatedError" in caplog.text
    assert "token-one" not in caplog.text
    assert "token-two" not in caplog.text


def test_firebase_credentials_error_is_configuration_error_without_secret_log(
    monkeypatch, caplog
):
    secret_path = "/app/secrets/private-service-account.json"
    provider, _, _ = _provider(monkeypatch, certificate_error=RuntimeError("bad key"))
    provider._config = FirebasePushProviderConfig("ok-dev", secret_path)

    with pytest.raises(PushProviderConfigurationError) as error:
        provider.send(_notification(), [_targets()[0]])

    assert "credentials" in str(error.value).lower()
    assert secret_path not in caplog.text
    assert "token-one" not in caplog.text


def test_noop_provider_and_factory_do_not_send():
    provider = build_push_provider(SimpleNamespace(PUSH_PROVIDER="noop"))

    deliveries = provider.send(_notification(), _targets())

    assert isinstance(provider, NoopPushProvider)
    assert [item.status for item in deliveries] == [
        PushDeliveryStatus.DISABLED,
        PushDeliveryStatus.DISABLED,
    ]
    with pytest.raises(PushProviderConfigurationError):
        build_push_provider(
            SimpleNamespace(
                PUSH_PROVIDER="fcm",
                FCM_PROJECT_ID="",
                GOOGLE_APPLICATION_CREDENTIALS="",
            )
        )


def test_factory_accepts_flask_config_and_requires_explicit_provider():
    app = Flask(__name__)
    app.config.update(PUSH_PROVIDER="fcm", FCM_PROJECT_ID="project", GOOGLE_APPLICATION_CREDENTIALS="/test/account.json")
    app.config["PUSH_WORKER_LEASE_SECONDS"] = 12
    provider = build_push_provider(app.config)
    assert isinstance(provider, FirebasePushProvider)
    assert provider._config.http_timeout_seconds == 4
    app.config["PUSH_WORKER_LEASE_SECONDS"] = 0
    with pytest.raises(PushProviderConfigurationError):
        build_push_provider(app.config)
    app.config["PUSH_WORKER_LEASE_SECONDS"] = 12
    for value in (None, "", "unsupported"):
        app.config["PUSH_PROVIDER"] = value
        with pytest.raises(PushProviderConfigurationError):
            build_push_provider(app.config)
    app.config.update(PUSH_PROVIDER="fcm", FCM_PROJECT_ID="")
    with pytest.raises(PushProviderConfigurationError):
        build_push_provider(app.config)
    assert 'token-one' not in repr(_targets()[0])


@pytest.mark.parametrize(
    "route",
    [
        "https://example.test",
        "//other.example",
        "/ok\nnext",
        "/\t/evil.example",
        "/\\evil.example",
    ],
)
def test_push_notification_rejects_unsafe_route(route):
    with pytest.raises(ValueError):
        PushNotification(uuid4(), "Title", "Body", route)
