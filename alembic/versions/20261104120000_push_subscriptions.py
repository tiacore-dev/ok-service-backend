"""Add push subscription registry.

Revision ID: 20261104120000
Revises: 20261103120000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20261104120000"
down_revision = "20261103120000"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "push_subscriptions",
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("browser_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("token", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.Column("revoked_at", sa.BigInteger()),
        sa.UniqueConstraint("user_id", "browser_id", name="uq_push_subscription_user_browser"),
        sa.CheckConstraint("platform = 'web'", name="ck_push_subscription_platform"),
        sa.CheckConstraint("length(trim(token)) > 0 AND token = trim(token) AND octet_length(token) <= 1024", name="ck_push_subscription_token"),
        sa.CheckConstraint("(active AND revoked_at IS NULL) OR (NOT active AND revoked_at IS NOT NULL)", name="ck_push_subscription_revoked"),
    )
    op.create_index("uq_push_subscription_active_browser", "push_subscriptions", ["browser_id"], unique=True, postgresql_where=sa.text("active"))
    op.create_index("uq_push_subscription_active_token", "push_subscriptions", ["token"], unique=True, postgresql_where=sa.text("active"))


def downgrade():
    op.drop_table("push_subscriptions")
