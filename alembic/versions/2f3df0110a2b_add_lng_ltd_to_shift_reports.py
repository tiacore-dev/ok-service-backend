"""add lng and ltd columns to shift reports

Revision ID: 2f3df0110a2b
Revises: 5ea2fe712409
Create Date: 2025-11-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f3df0110a2b"
down_revision: Union[str, None] = "5ea2fe712409"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shift_reports", sa.Column("lng", sa.Float(), nullable=True))
    op.add_column("shift_reports", sa.Column("ltd", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("shift_reports", "ltd")
    op.drop_column("shift_reports", "lng")
