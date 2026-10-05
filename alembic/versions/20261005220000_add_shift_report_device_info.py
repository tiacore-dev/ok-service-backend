"""Add start and finish device metadata to shift reports.

Revision ID: 20261005220000
Revises: 20261005210000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20261005220000"
down_revision: Union[str, None] = "20261005210000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shift_reports",
        sa.Column("start_device_info", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "shift_reports",
        sa.Column("finish_device_info", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("shift_reports", "finish_device_info")
    op.drop_column("shift_reports", "start_device_info")
