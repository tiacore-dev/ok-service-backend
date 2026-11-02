"""Add server-side authorization sessions and refresh-token lineage.

Revision ID: 20261105120000
Revises: 20261104120000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261105120000"
down_revision = "20261104120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("session_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
        ),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("revoked_at", sa.BigInteger(), nullable=True),
        sa.Column("current_token_jti", postgresql.UUID(as_uuid=True), nullable=False),
        sa.UniqueConstraint("current_token_jti", name="uq_auth_sessions_current_token_jti"),
    )
    op.create_index(
        "ix_auth_sessions_user_revoked", "auth_sessions", ["user_id", "revoked_at"]
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("jti", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_sessions.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
        ),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("used_at", sa.BigInteger(), nullable=True),
        sa.Column("revoked_at", sa.BigInteger(), nullable=True),
        sa.Column("replaced_by_jti", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_refresh_tokens_session_state",
        "refresh_tokens",
        ["session_id", "used_at", "revoked_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_session_state", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_auth_sessions_user_revoked", table_name="auth_sessions")
    op.drop_table("auth_sessions")
