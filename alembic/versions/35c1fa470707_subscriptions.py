"""Subscriptions

Revision ID: 35c1fa470707
Revises: 0b789327d492
Create Date: 2025-01-21 13:15:26.634683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '35c1fa470707'
down_revision: Union[str, None] = '0b789327d492'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'subscriptions',
        sa.Column('subscription_id', UUID(as_uuid=True), primary_key=True,
                  nullable=False),
        sa.Column('user', UUID(as_uuid=True), sa.ForeignKey(
            'users.user_id'), nullable=False),
        sa.Column('subscription_data', sa.Text, nullable=False)
    )


def downgrade():
    op.drop_table('subscriptions')
