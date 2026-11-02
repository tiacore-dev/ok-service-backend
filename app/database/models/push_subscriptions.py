from uuid import uuid4

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_milliseconds


class PushSubscriptions(Base):
    __tablename__ = "push_subscriptions"
    subscription_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    browser_id = Column(UUID(as_uuid=True), nullable=False)
    platform = Column(String(20), nullable=False)
    token = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at = Column(BigInteger, nullable=False, default=utc_epoch_milliseconds)
    updated_at = Column(BigInteger, nullable=False, default=utc_epoch_milliseconds)
    revoked_at = Column(BigInteger)
    __table_args__ = (
        UniqueConstraint("user_id", "browser_id", name="uq_push_subscription_user_browser"),
        CheckConstraint("platform = 'web'", name="ck_push_subscription_platform"),
        CheckConstraint("length(trim(token)) > 0 AND token = trim(token) AND octet_length(token) <= 1024", name="ck_push_subscription_token"),
        CheckConstraint("(active AND revoked_at IS NULL) OR (NOT active AND revoked_at IS NOT NULL)", name="ck_push_subscription_revoked"),
        Index("uq_push_subscription_active_browser", "browser_id", unique=True, postgresql_where=text("active")),
        Index("uq_push_subscription_active_token", "token", unique=True, postgresql_where=text("active")),
    )
