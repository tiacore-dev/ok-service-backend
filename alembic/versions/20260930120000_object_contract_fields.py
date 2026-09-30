"""Add contract and order fields to objects.

Revision ID: 20260930120000
Revises: 20260903090000
Create Date: 2026-09-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260930120000"
down_revision: Union[str, None] = "20260903090000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("objects", sa.Column("contract_start_date", sa.Date(), nullable=True))
    op.add_column("objects", sa.Column("contract_end_date", sa.Date(), nullable=True))
    op.add_column("objects", sa.Column("order_number", sa.Text(), nullable=True))
    op.add_column(
        "objects",
        sa.Column("monthly_ks_closing_date", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("objects", "monthly_ks_closing_date")
    op.drop_column("objects", "order_number")
    op.drop_column("objects", "contract_end_date")
    op.drop_column("objects", "contract_start_date")
