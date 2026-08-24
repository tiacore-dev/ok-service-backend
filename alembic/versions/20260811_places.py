"""Add places belonging to objects.

Revision ID: 20260811_places
Revises: 20260805_roles_list_permission
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260811_places"
down_revision: Union[str, None] = "20260805_roles_list_permission"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "places",
        sa.Column("place_id", sa.UUID(), nullable=False),
        sa.Column("object_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["object_id"], ["objects.object_id"]),
        sa.PrimaryKeyConstraint("place_id"),
    )


def downgrade() -> None:
    op.drop_table("places")
