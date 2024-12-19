"""Change logs message type

Revision ID: 550e12fff8ce
Revises: 76c74950d2e9
Create Date: 2024-12-19 21:20:25.347176

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '550e12fff8ce'
down_revision: Union[str, None] = '76c74950d2e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'logs',
        'message',
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False
    )


def downgrade() -> None:
    op.alter_column(
        'logs',
        'message',
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False
    )
