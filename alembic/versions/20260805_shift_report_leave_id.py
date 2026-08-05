"""Link cancelled shift reports to the leave that cancelled them.

Revision ID: 20260805_shift_report_leave_id
Revises: 20260804_epoch_milliseconds
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_shift_report_leave_id"
down_revision: Union[str, None] = "20260804_epoch_milliseconds"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shift_reports",
        sa.Column("leave_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_shift_reports_leave_id",
        "shift_reports",
        "leaves",
        ["leave_id"],
        ["leave_id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_shift_reports_leave_id", "shift_reports", type_="foreignkey")
    op.drop_column("shift_reports", "leave_id")
