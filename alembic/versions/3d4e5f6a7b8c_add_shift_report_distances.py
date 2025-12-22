"""add distance_start and distance_end to shift reports

Revision ID: 3d4e5f6a7b8c
Revises: 1c2b3d4e5f6a
Create Date: 2025-11-12 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3d4e5f6a7b8c"
down_revision: Union[str, None] = "1c2b3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shift_reports", sa.Column("distance_start", sa.Float(), nullable=True)
    )
    op.add_column("shift_reports", sa.Column("distance_end", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("shift_reports", "distance_end")
    op.drop_column("shift_reports", "distance_start")
