"""Add persistent notification content and recipient state.

Revision ID: 20261102120000
Revises: 20261102100000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261102120000"
down_revision = "20261102100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_type", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("related_entity_type", sa.String(length=100), nullable=True),
        sa.Column("related_entity_id", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            server_default=sa.text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "(related_entity_type IS NULL) = (related_entity_id IS NULL)",
            name="ck_notifications_related_entity_pair",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.user_id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("notification_id"),
    )
    op.create_index(
        "ix_notifications_created_at_id",
        "notifications",
        ["created_at", "notification_id"],
        unique=False,
    )
    op.create_table(
        "notification_recipients",
        sa.Column(
            "notification_recipient_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("notification_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "viewed", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("viewed_at", sa.BigInteger(), nullable=True),
        sa.Column("browser_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "viewed OR (viewed_at IS NULL AND browser_id IS NULL)",
            name="ck_notification_recipients_unviewed_metadata",
        ),
        sa.CheckConstraint(
            "NOT viewed OR (viewed_at IS NOT NULL AND browser_id IS NOT NULL)",
            name="ck_notification_recipients_view_metadata",
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.notification_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("notification_recipient_id"),
        sa.UniqueConstraint(
            "notification_id",
            "user_id",
            name="uq_notification_recipients_notification_user",
        ),
    )
    op.create_index(
        "ix_notification_recipients_user_viewed_notification",
        "notification_recipients",
        ["user_id", "viewed", "notification_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_recipients_user_viewed_notification",
        table_name="notification_recipients",
    )
    op.drop_table("notification_recipients")
    op.drop_index("ix_notifications_created_at_id", table_name="notifications")
    op.drop_table("notifications")
