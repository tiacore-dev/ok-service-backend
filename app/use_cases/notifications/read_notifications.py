from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.notifications import NotificationQueryValidationError, NotificationView

from .ports import NotificationRepository


DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def _validate_page(offset: int, limit: int) -> None:
    if offset < 0 or not 1 <= limit <= MAX_LIMIT:
        raise NotificationQueryValidationError(
            f"offset must be non-negative and limit must be between 1 and {MAX_LIMIT}"
        )


@dataclass(slots=True)
class ListNotificationHistoryUseCase:
    repository: NotificationRepository

    def execute(
        self, user_id: UUID, offset: int = 0, limit: int = DEFAULT_LIMIT
    ) -> list[NotificationView]:
        _validate_page(offset, limit)
        return self.repository.list_history(user_id, offset, limit)


@dataclass(slots=True)
class ListUnviewedNotificationsUseCase:
    repository: NotificationRepository

    def execute(
        self, user_id: UUID, offset: int = 0, limit: int = DEFAULT_LIMIT
    ) -> list[NotificationView]:
        _validate_page(offset, limit)
        return self.repository.list_unviewed(user_id, offset, limit)


@dataclass(slots=True)
class CountUnviewedNotificationsUseCase:
    repository: NotificationRepository

    def execute(self, user_id: UUID) -> int:
        return self.repository.count_unviewed(user_id)


@dataclass(slots=True)
class GetOwnNotificationUseCase:
    repository: NotificationRepository

    def execute(self, notification_id: UUID, user_id: UUID) -> NotificationView | None:
        return self.repository.get_for_user(notification_id, user_id)
