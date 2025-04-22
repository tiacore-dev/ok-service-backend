"""add project work name

Revision ID: 88852ee1fb1c
Revises: eb309edeb3fc
Create Date: 2025-04-22 11:21:31.557505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88852ee1fb1c'
down_revision: Union[str, None] = 'eb309edeb3fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_works',
                  sa.Column('project_work_name', sa.String(), nullable=True)
                  )


def downgrade() -> None:
    op.drop_column('project_works', 'project_work_name')
