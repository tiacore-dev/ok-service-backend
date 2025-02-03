"""No name in work prices

Revision ID: 8bbb9dfcec1b
Revises: 0b81397f8289
Create Date: 2025-02-03 10:25:09.997243

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bbb9dfcec1b'
down_revision: Union[str, None] = '0b81397f8289'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('work_prices', 'name')


def downgrade() -> None:
    op.add_column('work_prices', sa.Column(
        'name', sa.String()))
