"""Add shift standards reference.

Revision ID: 20261005200000
Revises: 20261005190000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261005200000"
down_revision: Union[str, None] = "20261005190000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shift_standards",
        sa.Column("shift_standard_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.Integer(), nullable=False),
        sa.Column("standard", sa.Float(), nullable=False),
        sa.Column("notification_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            server_default=sa.text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.CheckConstraint("standard > 0", name="check_shift_standards_standard_positive"),
        sa.ForeignKeyConstraint(["created_by"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("shift_standard_id"),
        sa.UniqueConstraint("category"),
    )


def downgrade() -> None:
    op.drop_table("shift_standards")
