"""Shift report date bigint

Revision ID: 0b81397f8289
Revises: 51564584ec74
Create Date: 2025-02-02 15:55:21.043833

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0b81397f8289'
down_revision: Union[str, None] = '51564584ec74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Изменяем тип колонки date с Integer на BigInteger
    op.alter_column('shift_reports', 'date',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)


def downgrade():
    # Возвращаем обратно в Integer, если нужно откатить
    op.alter_column('shift_reports', 'date',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=False)
