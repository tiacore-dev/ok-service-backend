"""Add short shift flag to shift reports.

Revision ID: 20261005210000
Revises: 20261005200000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20261005210000"
down_revision: Union[str, None] = "20261005200000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shift_reports",
        sa.Column(
            "short_shift",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("shift_reports", "short_shift")
