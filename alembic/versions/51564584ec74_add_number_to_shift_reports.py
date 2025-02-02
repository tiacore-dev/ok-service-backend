"""Add number to shift_reports

Revision ID: 51564584ec74
Revises: 35c1fa470707
Create Date: 2025-02-02 15:05:08.412622

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51564584ec74'
down_revision: Union[str, None] = '35c1fa470707'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('shift_reports', sa.Column(
        'number', sa.Integer(), autoincrement=True))


def downgrade() -> None:
    op.drop_column('shift_reports', 'number')
