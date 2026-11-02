from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Notification:
    notification_id: UUID
    notification_type: str
    title: str
    text: str
    created_at: int
    idempotency_key: str
    created_by: UUID | None = None
    link: str | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None


@dataclass(frozen=True, slots=True)
class NotificationView:
    notification_id: UUID
    notification_type: str
    title: str
    text: str
    created_at: int
    notification_recipient_id: UUID
    user_id: UUID
    viewed: bool
    viewed_at: int | None
    link: str | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    browser_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class NotificationRecipient:
    notification_recipient_id: UUID
    notification_id: UUID
    user_id: UUID
    viewed: bool
    viewed_at: int | None
    browser_id: UUID | None
