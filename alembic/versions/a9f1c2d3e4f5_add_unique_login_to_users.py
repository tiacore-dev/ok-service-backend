"""add unique constraint for users.login

Revision ID: a9f1c2d3e4f5
Revises: 3d4e5f6a7b8c
Create Date: 2025-02-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a9f1c2d3e4f5"
down_revision: Union[str, None] = "3d4e5f6a7b8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_users_login", "users", ["login"])


def downgrade() -> None:
    op.drop_constraint("uq_users_login", "users", type_="unique")
