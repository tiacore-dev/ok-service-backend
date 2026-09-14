"""add price to project works

Revision ID: 20260827120000
Revises: 20260818_place_rel_bulk
Create Date: 2026-08-27 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260827120000"
down_revision: Union[str, None] = "20260818_place_rel_bulk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_works",
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_works", "price")
