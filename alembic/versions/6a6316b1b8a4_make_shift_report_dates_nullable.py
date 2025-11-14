"""Make shift report date_start/date_end nullable

Revision ID: 6a6316b1b8a4
Revises: 2f3df0110a2b
Create Date: 2025-02-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6a6316b1b8a4"
down_revision: Union[str, None] = "2f3df0110a2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "shift_reports",
        "date_start",
        existing_type=sa.BigInteger(),
        nullable=True,
        existing_nullable=False,
        server_default=None,
        existing_server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
    )
    op.alter_column(
        "shift_reports",
        "date_end",
        existing_type=sa.BigInteger(),
        nullable=True,
        existing_nullable=False,
        server_default=None,
        existing_server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
    )


def downgrade() -> None:
    op.alter_column(
        "shift_reports",
        "date_start",
        existing_type=sa.BigInteger(),
        nullable=False,
        existing_nullable=True,
        server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
    )
    op.alter_column(
        "shift_reports",
        "date_end",
        existing_type=sa.BigInteger(),
        nullable=False,
        existing_nullable=True,
        server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
    )
