"""Bind active browser push subscriptions to server authorization sessions.

Revision ID: 20261106120000
Revises: 20261105120000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261106120000"
down_revision = "20261105120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Historical subscriptions cannot be safely attributed to an auth session.
    # Preserve their audit records but revoke active delivery eligibility; clients
    # register again using an authenticated, session-bound endpoint.
    op.add_column(
        "auth_sessions",
        sa.Column("browser_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "push_subscriptions",
        sa.Column("auth_session_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_push_subscriptions_auth_session",
        "push_subscriptions",
        "auth_sessions",
        ["auth_session_id"],
        ["session_id"],
        ondelete="CASCADE",
    )
    op.execute(
        "UPDATE push_subscriptions "
        "SET active = false, revoked_at = CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT), "
        "updated_at = CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT) "
        "WHERE active"
    )
    op.create_check_constraint(
        "ck_push_subscription_active_session",
        "push_subscriptions",
        "NOT active OR auth_session_id IS NOT NULL",
    )
    op.create_index(
        "ix_push_subscriptions_auth_session_active",
        "push_subscriptions",
        ["auth_session_id", "active"],
    )


def downgrade() -> None:
    op.drop_index("ix_push_subscriptions_auth_session_active", table_name="push_subscriptions")
    op.drop_constraint(
        "ck_push_subscription_active_session", "push_subscriptions", type_="check"
    )
    op.drop_constraint(
        "fk_push_subscriptions_auth_session", "push_subscriptions", type_="foreignkey"
    )
    op.drop_column("push_subscriptions", "auth_session_id")
    op.drop_column("auth_sessions", "browser_id")
