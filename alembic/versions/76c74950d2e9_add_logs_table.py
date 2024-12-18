"""Add Logs table

Revision ID: 76c74950d2e9
Revises: 8386d7581084
Create Date: 2024-12-18 15:37:45.665608

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision: str = '76c74950d2e9'
down_revision: Union[str, None] = '8386d7581084'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'logs',
        sa.Column('log_id', sa.UUID(), nullable=False),
        sa.Column('login', sa.String(255), nullable=False),  # Изменено
        sa.Column('action', sa.String(255), nullable=False),
        sa.Column('message', sa.String(255), nullable=False),
        sa.Column('timestamp', sa.DateTime, default=datetime.utcnow),
        sa.PrimaryKeyConstraint('log_id', name='logs_pkey')
    )


def downgrade() -> None:
    op.drop_table('logs')
