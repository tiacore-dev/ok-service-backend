from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.domain.notifications import Notification, NotificationRecipient, NotificationView


class NotificationCreationRepository(Protocol):
    def create_notification(
        self,
        notification: Notification,
        recipient_user_ids: tuple[UUID, ...],
    ) -> Notification: ...


class NotificationRepository(NotificationCreationRepository, Protocol):

    def list_history(
        self, user_id: UUID, offset: int, limit: int
    ) -> list[NotificationView]: ...

    def list_unviewed(
        self, user_id: UUID, offset: int, limit: int
    ) -> list[NotificationView]: ...

    def count_unviewed(self, user_id: UUID) -> int: ...

    def get_for_user(
        self, notification_id: UUID, user_id: UUID
    ) -> NotificationView | None: ...

    def mark_viewed(
        self, notification_id: UUID, user_id: UUID, browser_id: UUID
    ) -> NotificationRecipient | None: ...
