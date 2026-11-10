"""Add a self-referencing parent to work categories.

Revision ID: 20261110120000
Revises: 20261108120000

Existing categories keep ``parent_id = NULL`` and stay root-level.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261110120000"
down_revision: Union[str, None] = "20261108120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "work_categories",
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_work_categories_parent_id",
        "work_categories",
        "work_categories",
        ["parent_id"],
        ["work_category_id"],
    )
    op.create_index(
        "ix_work_categories_parent_id", "work_categories", ["parent_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_work_categories_parent_id", table_name="work_categories")
    op.drop_constraint(
        "fk_work_categories_parent_id", "work_categories", type_="foreignkey"
    )
    op.drop_column("work_categories", "parent_id")
