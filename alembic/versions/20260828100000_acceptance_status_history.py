"""add acceptance status history

Revision ID: 20260828100000
Revises: 20260827150000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260828100000"
down_revision: Union[str, None] = "20260827150000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "acceptance_status_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("acceptance_id", sa.UUID(), nullable=False),
        sa.Column("changed_at", sa.BigInteger(), nullable=False),
        sa.Column("changed_by", sa.UUID(), nullable=False),
        sa.Column("from_status", sa.String(), nullable=False),
        sa.Column("to_status", sa.String(), nullable=False),
        sa.CheckConstraint(
            "from_status IN ('presented', 'violations_found', 'accepted_on_site', 'documents_signed')",
            name="check_acceptance_history_from_status",
        ),
        sa.CheckConstraint(
            "to_status IN ('presented', 'violations_found', 'accepted_on_site', 'documents_signed')",
            name="check_acceptance_history_to_status",
        ),
        sa.ForeignKeyConstraint(["acceptance_id"], ["acceptances.id"]),
        sa.ForeignKeyConstraint(["changed_by"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("acceptance_status_history")
