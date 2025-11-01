"""add shift report date range and object coordinates

Revision ID: 7f1d5c3f1bf2
Revises: 755c46649157
Create Date: 2025-05-04 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7f1d5c3f1bf2"
down_revision: Union[str, None] = "755c46649157"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Shift report date range columns
    op.add_column(
        "shift_reports",
        sa.Column(
            "date_start",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
        ),
    )
    op.add_column(
        "shift_reports",
        sa.Column(
            "date_end",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
        ),
    )
    op.execute(
        "UPDATE shift_reports SET date_start = date, date_end = date"
    )

    # Object coordinates columns
    op.add_column(
        "objects",
        sa.Column("lng", sa.Float(), nullable=True, server_default=sa.text("0")),
    )
    op.add_column(
        "objects",
        sa.Column("ltd", sa.Float(), nullable=True, server_default=sa.text("0")),
    )


def downgrade():
    op.drop_column("objects", "ltd")
    op.drop_column("objects", "lng")
    op.drop_column("shift_reports", "date_end")
    op.drop_column("shift_reports", "date_start")
