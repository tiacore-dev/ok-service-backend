"""Add positions and user active flag

Revision ID: 8ab65f512540
Revises: e1f4b8a9c2d1
Create Date: 2026-07-08 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8ab65f512540"
down_revision: Union[str, None] = "e1f4b8a9c2d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "positions",
        sa.Column(
            "position_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column("position_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.create_foreign_key(
        "users_position_id_fkey",
        "users",
        "positions",
        ["position_id"],
        ["position_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("users_position_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "is_active")
    op.drop_column("users", "position_id")
    op.drop_table("positions")
