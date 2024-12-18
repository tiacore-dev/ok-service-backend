"""Add role column to users

Revision ID: 8386d7581084
Revises: 316f305c821a
Create Date: 2024-12-18 12:31:44.047364

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8386d7581084'
down_revision: Union[str, None] = '316f305c821a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('users', sa.Column('role', sa.String(), nullable=False))
    op.create_foreign_key('users_role_fkey', 'users', 'roles', ['role'], ['role_id'])

def downgrade():
    op.drop_constraint('users_role_fkey', 'users', type_='foreignkey')
    op.drop_column('users', 'role')
