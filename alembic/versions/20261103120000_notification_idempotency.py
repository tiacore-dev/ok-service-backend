"""Add caller supplied idempotency keys to notifications.

Revision ID: 20261103120000
Revises: 20261102120000
"""

from alembic import op
import sqlalchemy as sa


revision = "20261103120000"
down_revision = "20261102120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
    )
    op.create_check_constraint(
        "ck_notifications_idempotency_key_nonempty",
        "notifications",
        "idempotency_key IS NULL OR length(trim(idempotency_key)) > 0",
    )
    op.create_unique_constraint(
        "uq_notifications_idempotency_key", "notifications", ["idempotency_key"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_notifications_idempotency_key", "notifications", type_="unique"
    )
    op.drop_constraint(
        "ck_notifications_idempotency_key_nonempty", "notifications", type_="check"
    )
    op.drop_column("notifications", "idempotency_key")
