"""Add leaves table and absence reason enum

Revision ID: b2a78f94f3d1
Revises: ae0d7dc1f6f4
Create Date: 2025-02-07 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2a78f94f3d1"
down_revision: Union[str, None] = "ae0d7dc1f6f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

absence_reason_enum = postgresql.ENUM(
    "vacation", "sick_leave", "day_off", name="absence_reason_enum", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    existing_enums = {enum["name"] for enum in inspect(bind).get_enums()}  # type: ignore
    if "absence_reason_enum" not in existing_enums:
        absence_reason_enum.create(bind)

    op.create_table(
        "leaves",
        sa.Column("leave_id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("start_date", sa.BigInteger(), nullable=False),
        sa.Column("end_date", sa.BigInteger(), nullable=False),
        sa.Column("reason", absence_reason_enum, nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("responsible_id", sa.UUID(), nullable=False),
        sa.Column("comment", sa.String(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
        sa.Column(
            "deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.user_id"], name="fk_leaves_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["responsible_id"],
            ["users.user_id"],
            name="fk_leaves_responsible_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.user_id"],
            name="fk_leaves_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.user_id"],
            name="fk_leaves_updated_by",
        ),
    )


def downgrade() -> None:
    op.drop_table("leaves")
    bind = op.get_bind()
    existing_enums = {enum["name"] for enum in inspect(bind).get_enums()}  # type: ignore
    if "absence_reason_enum" in existing_enums:
        absence_reason_enum.drop(bind)
