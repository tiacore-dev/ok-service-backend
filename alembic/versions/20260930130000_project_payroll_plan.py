"""Add payroll plan to projects.

Revision ID: 20260930130000
Revises: 20260930120000
Create Date: 2026-09-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260930130000"
down_revision: Union[str, None] = "20260930120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("payroll_plan", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "payroll_plan")
