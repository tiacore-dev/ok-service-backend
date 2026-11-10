from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.domain.notifications import (
    Notification,
    NotificationRecipientsRequiredError,
    NotificationValidationError,
)
from app.use_cases.time_utils import utc_epoch_milliseconds

from .ports import NotificationCreationRepository


@dataclass(frozen=True, slots=True)
class CreateNotificationCommand:
    idempotency_key: str
    notification_type: str
    title: str
    text: str
    recipient_user_ids: tuple[UUID, ...]
    created_by: UUID | None = None
    link: str | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None


@dataclass(slots=True)
class CreateNotificationUseCase:
    repository: NotificationCreationRepository

    def execute(self, command: CreateNotificationCommand) -> Notification:
        idempotency_key = command.idempotency_key.strip()
        if not idempotency_key or len(idempotency_key) > 255:
            raise NotificationValidationError(
                "idempotency_key must contain 1 to 255 characters"
            )
        if len(command.notification_type) > 100:
            raise NotificationValidationError(
                "notification_type must contain at most 100 characters"
            )
        if len(command.title) > 255:
            raise NotificationValidationError(
                "title must contain at most 255 characters"
            )
        if len(command.related_entity_type or "") > 100:
            raise NotificationValidationError(
                "related_entity_type must contain at most 100 characters"
            )
        if len(command.related_entity_id or "") > 100:
            raise NotificationValidationError(
                "related_entity_id must contain at most 100 characters"
            )
        if (command.related_entity_type is None) != (command.related_entity_id is None):
            raise NotificationValidationError(
                "related_entity_type and related_entity_id must be set together"
            )
        recipients = tuple(dict.fromkeys(command.recipient_user_ids))
        if not recipients:
            raise NotificationRecipientsRequiredError(
                "At least one notification recipient is required"
            )
        notification = Notification(
            notification_id=uuid4(),
            notification_type=command.notification_type,
            title=command.title,
            text=command.text,
            created_at=utc_epoch_milliseconds(),
            created_by=command.created_by,
            link=command.link,
            related_entity_type=command.related_entity_type,
            related_entity_id=command.related_entity_id,
            idempotency_key=idempotency_key,
        )
        return self.repository.create_notification(notification, recipients)
