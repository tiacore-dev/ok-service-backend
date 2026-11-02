from __future__ import annotations

from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert

from app.database import db_globals
from app.database.models.notifications import NotificationRecipients, Notifications
from app.domain.notifications import (
    Notification,
    NotificationIdempotencyConflictError,
    NotificationRecipient,
    NotificationView,
)


class _NotificationRecord(TypedDict):
    notification_id: UUID
    notification_type: str
    title: str
    text: str
    created_at: int
    created_by: UUID | None
    link: str | None
    related_entity_type: str | None
    related_entity_id: str | None
    idempotency_key: str | None


class _NotificationRecipientRecord(TypedDict):
    notification_recipient_id: UUID
    notification_id: UUID
    user_id: UUID
    viewed: bool
    viewed_at: int | None
    browser_id: UUID | None


class SQLAlchemyNotificationRepository:
    @staticmethod
    def _session_factory():
        session_factory = db_globals.Session
        if session_factory is None:
            raise RuntimeError("Database session is not initialized")
        return session_factory

    @staticmethod
    def _notification(record: Notifications) -> Notification:
        row = cast(_NotificationRecord, record.__dict__)
        idempotency_key = row["idempotency_key"]
        if idempotency_key is None:
            raise RuntimeError("New notification is missing its idempotency key")
        return Notification(
            notification_id=row["notification_id"],
            notification_type=row["notification_type"],
            title=row["title"],
            text=row["text"],
            created_at=row["created_at"],
            created_by=row["created_by"],
            link=row["link"],
            related_entity_type=row["related_entity_type"],
            related_entity_id=row["related_entity_id"],
            idempotency_key=idempotency_key,
        )

    @staticmethod
    def _view(
        notification: Notifications, recipient: NotificationRecipients
    ) -> NotificationView:
        notification_row = cast(_NotificationRecord, notification.__dict__)
        recipient_row = cast(_NotificationRecipientRecord, recipient.__dict__)
        return NotificationView(
            notification_id=notification_row["notification_id"],
            notification_type=notification_row["notification_type"],
            title=notification_row["title"],
            text=notification_row["text"],
            created_at=notification_row["created_at"],
            notification_recipient_id=recipient_row["notification_recipient_id"],
            user_id=recipient_row["user_id"],
            viewed=recipient_row["viewed"],
            viewed_at=recipient_row["viewed_at"],
            link=notification_row["link"],
            related_entity_type=notification_row["related_entity_type"],
            related_entity_id=notification_row["related_entity_id"],
            browser_id=recipient_row["browser_id"],
        )

    @staticmethod
    def _same_request(
        existing: Notifications,
        notification: Notification,
        existing_recipients: set[UUID],
        requested_recipients: tuple[UUID, ...],
    ) -> bool:
        existing_row = cast(_NotificationRecord, existing.__dict__)
        return (
            existing_row["notification_type"] == notification.notification_type
            and existing_row["title"] == notification.title
            and existing_row["text"] == notification.text
            and existing_row["link"] == notification.link
            and existing_row["related_entity_type"]
            == notification.related_entity_type
            and existing_row["related_entity_id"] == notification.related_entity_id
            and existing_row["created_by"] == notification.created_by
            and existing_recipients == set(requested_recipients)
        )

    @staticmethod
    def _recipient(record: NotificationRecipients) -> NotificationRecipient:
        row = cast(_NotificationRecipientRecord, record.__dict__)
        return NotificationRecipient(
            notification_recipient_id=row["notification_recipient_id"],
            notification_id=row["notification_id"],
            user_id=row["user_id"],
            viewed=row["viewed"],
            viewed_at=row["viewed_at"],
            browser_id=row["browser_id"],
        )

    def create_notification(
        self,
        notification: Notification,
        recipient_user_ids: tuple[UUID, ...],
    ) -> Notification:
        session_factory = self._session_factory()
        session = session_factory()
        try:
            with session.begin():
                values = {
                    "notification_id": notification.notification_id,
                    "notification_type": notification.notification_type,
                    "title": notification.title,
                    "text": notification.text,
                    "created_at": notification.created_at,
                    "created_by": notification.created_by,
                    "link": notification.link,
                    "related_entity_type": notification.related_entity_type,
                    "related_entity_id": notification.related_entity_id,
                    "idempotency_key": notification.idempotency_key,
                }
                statement = (
                    insert(Notifications)
                    .values(**values)
                    .on_conflict_do_nothing(
                        index_elements=[Notifications.idempotency_key]
                    )
                    .returning(Notifications)
                )
                record = session.execute(statement).scalar_one_or_none()
                if record is not None:
                    recipient_rows = [
                        {
                            "notification_id": notification.notification_id,
                            "user_id": user_id,
                        }
                        for user_id in recipient_user_ids
                    ]
                    session.execute(insert(NotificationRecipients), recipient_rows)
                    return self._notification(record)

                existing = session.execute(
                    select(Notifications).where(
                        Notifications.idempotency_key == notification.idempotency_key
                    )
                ).scalar_one_or_none()
                if existing is None:
                    raise RuntimeError("Idempotency key conflict row was not found")
                existing_recipients = set(
                    session.scalars(
                        select(NotificationRecipients.user_id).where(
                            NotificationRecipients.notification_id
                            == existing.notification_id
                        )
                    )
                )
                if not self._same_request(
                    existing, notification, existing_recipients, recipient_user_ids
                ):
                    raise NotificationIdempotencyConflictError(
                        "Idempotency key was already used with different notification data"
                    )
                return self._notification(existing)
        finally:
            session.close()

    def _list_for_user(
        self, user_id: UUID, offset: int, limit: int, *, unviewed_only: bool
    ) -> list[NotificationView]:
        session_factory = self._session_factory()
        with session_factory() as session:
            statement = select(Notifications, NotificationRecipients).join(
                NotificationRecipients,
                NotificationRecipients.notification_id == Notifications.notification_id,
            ).where(NotificationRecipients.user_id == user_id)
            if unviewed_only:
                statement = statement.where(NotificationRecipients.viewed.is_(False))
            rows = session.execute(
                statement.order_by(
                    Notifications.created_at.desc(),
                    Notifications.notification_id.desc(),
                )
                .offset(offset)
                .limit(limit)
            ).all()
            return [self._view(notification, recipient) for notification, recipient in rows]

    def list_history(
        self, user_id: UUID, offset: int, limit: int
    ) -> list[NotificationView]:
        return self._list_for_user(user_id, offset, limit, unviewed_only=False)

    def list_unviewed(
        self, user_id: UUID, offset: int, limit: int
    ) -> list[NotificationView]:
        return self._list_for_user(user_id, offset, limit, unviewed_only=True)

    def count_unviewed(self, user_id: UUID) -> int:
        session_factory = self._session_factory()
        with session_factory() as session:
            return int(
                session.scalar(
                    select(func.count())
                    .select_from(NotificationRecipients)
                    .where(
                        NotificationRecipients.user_id == user_id,
                        NotificationRecipients.viewed.is_(False),
                    )
                )
                or 0
            )

    def get_for_user(
        self, notification_id: UUID, user_id: UUID
    ) -> NotificationView | None:
        session_factory = self._session_factory()
        with session_factory() as session:
            row = session.execute(
                select(Notifications, NotificationRecipients)
                .join(
                    NotificationRecipients,
                    NotificationRecipients.notification_id
                    == Notifications.notification_id,
                )
                .where(
                    Notifications.notification_id == notification_id,
                    NotificationRecipients.user_id == user_id,
                )
            ).one_or_none()
            return self._view(*row) if row is not None else None

    def mark_viewed(
        self, notification_id: UUID, user_id: UUID, browser_id: UUID
    ) -> NotificationRecipient | None:
        session_factory = self._session_factory()
        session = session_factory()
        try:
            with session.begin():
                updated = session.execute(
                    update(NotificationRecipients)
                    .where(
                        NotificationRecipients.notification_id == notification_id,
                        NotificationRecipients.user_id == user_id,
                        NotificationRecipients.viewed.is_(False),
                    )
                    .values(
                        viewed=True,
                        # PostgreSQL wall clock is evaluated after a lock wait.
                        viewed_at=text(
                            "CAST(EXTRACT(EPOCH FROM clock_timestamp()) * 1000 AS BIGINT)"
                        ),
                        browser_id=browser_id,
                    )
                    .returning(NotificationRecipients)
                ).scalar_one_or_none()
                if updated is not None:
                    return self._recipient(updated)
                existing = session.execute(
                    select(NotificationRecipients).where(
                        NotificationRecipients.notification_id == notification_id,
                        NotificationRecipients.user_id == user_id,
                    )
                ).scalar_one_or_none()
                return self._recipient(existing) if existing is not None else None
        finally:
            session.close()
