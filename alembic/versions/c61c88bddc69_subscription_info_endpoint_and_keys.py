"""Subscription info: endpoint and keys

Revision ID: c61c88bddc69
Revises: 9b7464cf2368
Create Date: 2025-02-21 12:30:37.408211

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c61c88bddc69'
down_revision: Union[str, None] = '9b7464cf2368'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("subscriptions", sa.Column(
        'endpoint', sa.Text(), nullable=False
    ))

    op.add_column("subscriptions", sa.Column(
        'keys', sa.Text(), nullable=False
    ))

    op.drop_column("subscriptions",
                   'subscription_data')


def downgrade() -> None:
    op.drop_column("subscriptions",
                   'endpoint'
                   )

    op.drop_column("subscriptions",
                   'keys')

    op.add_column("subscriptions", sa.Column(
        'subscription_data', sa.Text(), nullable=False
    ))
