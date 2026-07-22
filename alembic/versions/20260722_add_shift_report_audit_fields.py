"""Add audit fields to shift reports.

Revision ID: 20260722_shift_report_audit
Revises: b7c8d9e0f1a2
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260722_shift_report_audit"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shift_reports", sa.Column("signed_at", sa.BigInteger(), nullable=True)
    )
    op.add_column("shift_reports", sa.Column("signed_by", sa.UUID(), nullable=True))
    op.add_column(
        "shift_reports", sa.Column("updated_at", sa.BigInteger(), nullable=True)
    )
    op.add_column("shift_reports", sa.Column("updated_by", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_shift_reports_signed_by",
        "shift_reports",
        "users",
        ["signed_by"],
        ["user_id"],
    )
    op.create_foreign_key(
        "fk_shift_reports_updated_by",
        "shift_reports",
        "users",
        ["updated_by"],
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_shift_reports_updated_by", "shift_reports", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_shift_reports_signed_by", "shift_reports", type_="foreignkey"
    )
    op.drop_column("shift_reports", "updated_by")
    op.drop_column("shift_reports", "updated_at")
    op.drop_column("shift_reports", "signed_by")
    op.drop_column("shift_reports", "signed_at")
