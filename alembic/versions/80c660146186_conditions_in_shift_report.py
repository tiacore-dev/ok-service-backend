"""Conditions in shift report

Revision ID: 80c660146186
Revises: f0bed8fba6e4
Create Date: 2025-02-07 11:51:40.195946

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80c660146186'
down_revision: Union[str, None] = 'f0bed8fba6e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем новый столбец с типом Integer и default значением в формате timestamp
    op.add_column("shift_reports", sa.Column(
        'night_shift', sa.Boolean(), nullable=False, default=False))
    # Добавляем новый столбец created_by
    op.add_column('shift_reports', sa.Column(
        'extreme_conditions', sa.Boolean(), nullable=False, default=False))


def downgrade() -> None:
    op.drop_column("shift_reports", "night_shift")
    op.drop_column("shift_reports", "extreme_conditions")
