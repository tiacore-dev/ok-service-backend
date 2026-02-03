"""add comment to shift_reports

Revision ID: b7c8d9e0f1a2
Revises: a9f1c2d3e4f5
Create Date: 2026-02-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a9f1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shift_reports", sa.Column("comment", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("shift_reports", "comment")
