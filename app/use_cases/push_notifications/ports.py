from __future__ import annotations

from typing import Protocol, Sequence

from app.domain.push_notifications import PushDelivery, PushNotification, PushTarget


class PushProviderConfigurationError(RuntimeError):
    """Firebase cannot be initialized with the configured application settings."""


class PushProvider(Protocol):
    def send(
        self, notification: PushNotification, targets: Sequence[PushTarget]
    ) -> list[PushDelivery]: ...
