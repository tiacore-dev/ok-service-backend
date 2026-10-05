"""Add start and finish browser IDs to shift reports.

Revision ID: 20261005230000
Revises: 20261005220000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261005230000"
down_revision: Union[str, None] = "20261005220000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The previous draft used JSONB fields. They may exist in an environment
    # where that draft was applied, but are absent on a clean database.
    op.execute(
        "ALTER TABLE shift_reports "
        "DROP COLUMN IF EXISTS start_device_info"
    )
    op.execute(
        "ALTER TABLE shift_reports "
        "DROP COLUMN IF EXISTS finish_device_info"
    )
    op.add_column(
        "shift_reports",
        sa.Column("start_browser_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "shift_reports",
        sa.Column("finish_browser_id", sa.UUID(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("shift_reports", "finish_browser_id")
    op.drop_column("shift_reports", "start_browser_id")
