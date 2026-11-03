"""Administrative broadcast validation and use of the notification producer."""
from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import unquote, urlsplit
from uuid import UUID
import re

from app.domain.notifications import NotificationValidationError
from .create_notification import CreateNotificationCommand, CreateNotificationUseCase
from .ports import NotificationCreationRepository


class BulkForbiddenError(Exception):
    pass


class BulkRecipientsError(Exception):
    pass


@dataclass(slots=True)
class BulkNotificationUseCase:
    repository: NotificationCreationRepository

    def execute(self, actor_id: UUID, recipients: tuple[UUID, ...], title: str,
                text: str, link: str | None, key: str):
        if not 1 <= len(recipients) <= 100 or len(set(recipients)) != len(recipients):
            raise NotificationValidationError("Provide 1 to 100 distinct recipients")
        if not title.strip() or len(title) > 255 or not text.strip() or len(text) > 4000:
            raise NotificationValidationError("Invalid title or text")
        if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", key):
            raise NotificationValidationError("Invalid idempotency key")
        if link is not None:
            decoded = unquote(link)
            try:
                parsed = urlsplit(decoded)
            except ValueError as error:
                raise NotificationValidationError("Invalid relative link") from error
            if (len(link) > 2048 or not decoded.startswith('/') or decoded.startswith('//')
                    or '\\' in decoded or '%' in decoded or parsed.scheme or parsed.netloc
                    or any(ord(c) < 32 or ord(c) == 127 for c in decoded)):
                raise NotificationValidationError("Invalid relative link")
        scoped_key = "admin-bulk:" + sha256(f"{actor_id}:{key}".encode()).hexdigest()
        return CreateNotificationUseCase(self.repository).execute(
            CreateNotificationCommand(scoped_key, "admin.bulk", title, text, recipients,
                                      created_by=actor_id, link=link)
        )
