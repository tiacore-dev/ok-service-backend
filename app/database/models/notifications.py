from uuid import uuid4

from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    text as sql_text,
)

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_milliseconds


class Notifications(Base):
    """Shared notification content and its originating event or broadcast."""

    __tablename__ = "notifications"

    notification_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    notification_type = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    link = Column(Text, nullable=True)
    related_entity_type = Column(String(100), nullable=True)
    related_entity_id = Column(String(100), nullable=True)
    created_at = Column(
        BigInteger,
        default=utc_epoch_milliseconds,
        server_default=sql_text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
        nullable=False,
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )
    idempotency_key = Column(String(255), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "(related_entity_type IS NULL) = (related_entity_id IS NULL)",
            name="ck_notifications_related_entity_pair",
        ),
        CheckConstraint(
            "idempotency_key IS NULL OR length(trim(idempotency_key)) > 0",
            name="ck_notifications_idempotency_key_nonempty",
        ),
        UniqueConstraint("idempotency_key", name="uq_notifications_idempotency_key"),
        Index("ix_notifications_created_at_id", "created_at", "notification_id"),
    )


class NotificationRecipients(Base):
    """Per-user state for a notification, including its first recorded view."""

    __tablename__ = "notification_recipients"

    notification_recipient_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    notification_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notifications.notification_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    viewed = Column(Boolean, nullable=False, default=False, server_default="false")
    viewed_at = Column(BigInteger, nullable=True)
    browser_id = Column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "notification_id",
            "user_id",
            name="uq_notification_recipients_notification_user",
        ),
        CheckConstraint(
            "viewed OR (viewed_at IS NULL AND browser_id IS NULL)",
            name="ck_notification_recipients_unviewed_metadata",
        ),
        CheckConstraint(
            "NOT viewed OR (viewed_at IS NOT NULL AND browser_id IS NOT NULL)",
            name="ck_notification_recipients_view_metadata",
        ),
        Index(
            "ix_notification_recipients_user_viewed_notification",
            "user_id",
            "viewed",
            "notification_id",
        ),
    )
