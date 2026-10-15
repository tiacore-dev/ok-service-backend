"""add price and summ to project materials

Revision ID: 20261005190000
Revises: 20260930130000
Create Date: 2026-10-05 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261005190000"
down_revision: Union[str, None] = "20260930130000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_materials",
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=True),
    )
    op.add_column(
        "project_materials",
        sa.Column("summ", sa.Numeric(precision=20, scale=4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_materials", "summ")
    op.drop_column("project_materials", "price")
