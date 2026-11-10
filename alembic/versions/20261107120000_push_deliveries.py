"""Add the durable PostgreSQL push delivery queue.

Revision ID: 20261107120000
Revises: 20261106120000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261107120000"
down_revision = "20261106120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_deliveries",
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("notification_recipient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.BigInteger(), nullable=False),
        sa.Column("locked_until", sa.BigInteger()),
        sa.Column("locked_by", sa.String(128)),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True)),
        sa.Column("sent_at", sa.BigInteger()),
        sa.Column("provider_message_id", sa.String(512)),
        sa.Column("last_error", sa.String(512)),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["notification_recipient_id"], ["notification_recipients.notification_recipient_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["push_subscriptions.subscription_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("notification_recipient_id", "subscription_id", name="uq_push_deliveries_recipient_subscription"),
        sa.CheckConstraint("status IN ('pending', 'processing', 'sent', 'retry', 'failed')", name="ck_push_deliveries_status"),
        sa.CheckConstraint("attempts >= 0", name="ck_push_deliveries_attempts"),
        sa.CheckConstraint("(status = 'processing') = (locked_until IS NOT NULL AND locked_by IS NOT NULL AND lease_token IS NOT NULL)", name="ck_push_deliveries_lease"),
        sa.CheckConstraint("(status = 'sent') = (sent_at IS NOT NULL)", name="ck_push_deliveries_sent_at"),
    )
    op.create_index("ix_push_deliveries_ready", "push_deliveries", ["status", "next_attempt_at"])
    op.create_index("ix_push_deliveries_lease", "push_deliveries", ["status", "locked_until"])


def downgrade() -> None:
    op.drop_index("ix_push_deliveries_lease", table_name="push_deliveries")
    op.drop_index("ix_push_deliveries_ready", table_name="push_deliveries")
    op.drop_table("push_deliveries")
