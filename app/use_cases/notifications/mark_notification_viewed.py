from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.notifications import NotificationRecipient

from .ports import NotificationRepository


@dataclass(slots=True)
class MarkNotificationViewedUseCase:
    repository: NotificationRepository

    def execute(
        self, notification_id: UUID, current_user_id: UUID, browser_id: UUID
    ) -> NotificationRecipient | None:
        """Return None unless this notification belongs to the current user."""
        return self.repository.mark_viewed(
            notification_id, current_user_id, browser_id
        )
