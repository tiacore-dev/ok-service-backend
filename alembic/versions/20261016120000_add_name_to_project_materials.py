"""add name to project materials

Revision ID: 20261016120000
Revises: 20261007090000
Create Date: 2026-10-16 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261016120000"
down_revision: Union[str, None] = "20261007090000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_materials",
        sa.Column("project_material_name", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_materials", "project_material_name")
