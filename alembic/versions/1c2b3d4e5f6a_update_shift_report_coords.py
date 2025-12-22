"""rename lng/ltd to lng_start/ltd_start and add end coords

Revision ID: 1c2b3d4e5f6a
Revises: 6a6316b1b8a4
Create Date: 2025-11-12 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c2b3d4e5f6a"
down_revision: Union[str, None] = "6a6316b1b8a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("shift_reports", "lng", new_column_name="lng_start")
    op.alter_column("shift_reports", "ltd", new_column_name="ltd_start")
    op.add_column("shift_reports", sa.Column("lng_end", sa.Float(), nullable=True))
    op.add_column("shift_reports", sa.Column("ltd_end", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("shift_reports", "ltd_end")
    op.drop_column("shift_reports", "lng_end")
    op.alter_column("shift_reports", "ltd_start", new_column_name="ltd")
    op.alter_column("shift_reports", "lng_start", new_column_name="lng")
