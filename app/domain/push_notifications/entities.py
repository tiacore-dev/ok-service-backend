from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class PushDeliveryStatus(StrEnum):
    SENT = "sent"
    TEMPORARY_FAILURE = "temporary_failure"
    INVALID_TOKEN = "invalid_token"
    CONFIGURATION_ERROR = "configuration_error"
    DISABLED = "disabled"


@dataclass(frozen=True, slots=True)
class PushTarget:
    """A registry row and its FCM token; the token must never be logged."""

    subscription_id: UUID
    token: str


@dataclass(frozen=True, slots=True)
class PushNotification:
    notification_id: UUID
    title: str
    body: str
    route: str

    def __post_init__(self) -> None:
        if not self.route.startswith("/") or self.route.startswith("//"):
            raise ValueError("Push route must be an application-relative path")
        if any(
            ord(character) < 0x20 or ord(character) == 0x7F or character == "\\"
            for character in self.route
        ):
            raise ValueError("Push route contains control characters or backslash")


@dataclass(frozen=True, slots=True)
class PushDelivery:
    subscription_id: UUID
    status: PushDeliveryStatus
    provider_message_id: str | None = None
    error_code: str | None = None
