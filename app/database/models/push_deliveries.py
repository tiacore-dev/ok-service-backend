from uuid import uuid4

from sqlalchemy import BigInteger, CheckConstraint, Column, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_milliseconds


class PushDeliveries(Base):
    """Durable, per-device delivery work for one personal notification."""

    __tablename__ = "push_deliveries"

    delivery_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    notification_recipient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("notification_recipients.notification_recipient_id", ondelete="CASCADE"),
        nullable=False,
    )
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("push_subscriptions.subscription_id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(16), nullable=False, default="pending", server_default=text("'pending'"))
    attempts = Column(Integer, nullable=False, default=0, server_default=text("0"))
    next_attempt_at = Column(BigInteger, nullable=False, default=utc_epoch_milliseconds)
    locked_until = Column(BigInteger)
    locked_by = Column(String(128))
    lease_token = Column(UUID(as_uuid=True))
    sent_at = Column(BigInteger)
    provider_message_id = Column(String(512))
    last_error = Column(String(512))
    created_at = Column(BigInteger, nullable=False, default=utc_epoch_milliseconds)
    updated_at = Column(BigInteger, nullable=False, default=utc_epoch_milliseconds)

    __table_args__ = (
        UniqueConstraint(
            "notification_recipient_id", "subscription_id",
            name="uq_push_deliveries_recipient_subscription",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'sent', 'retry', 'failed')",
            name="ck_push_deliveries_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_push_deliveries_attempts"),
        CheckConstraint(
            "(status = 'processing') = (locked_until IS NOT NULL AND locked_by IS NOT NULL AND lease_token IS NOT NULL)",
            name="ck_push_deliveries_lease",
        ),
        CheckConstraint(
            "(status = 'sent') = (sent_at IS NOT NULL)",
            name="ck_push_deliveries_sent_at",
        ),
        Index("ix_push_deliveries_ready", "status", "next_attempt_at"),
        Index("ix_push_deliveries_lease", "status", "locked_until"),
    )
