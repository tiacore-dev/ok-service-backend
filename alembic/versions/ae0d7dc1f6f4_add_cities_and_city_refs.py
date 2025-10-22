"""Add cities entity and link to users and objects

Revision ID: ae0d7dc1f6f4
Revises: 755c46649157
Create Date: 2025-02-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ae0d7dc1f6f4"
down_revision: Union[str, None] = "755c46649157"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cities",
        sa.Column("city_id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column(
            "deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )
    op.create_foreign_key(
        "cities_created_by_fkey",
        "cities",
        "users",
        ["created_by"],
        ["user_id"],
        ondelete="CASCADE",
    )

    op.add_column("objects", sa.Column("city_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_objects_city_id",
        "objects",
        "cities",
        ["city_id"],
        ["city_id"],
        ondelete="SET NULL",
    )

    op.add_column("users", sa.Column("city_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "users_city_id_fkey",
        "users",
        "cities",
        ["city_id"],
        ["city_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("users_city_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "city_id")

    op.drop_constraint("fk_objects_city_id", "objects", type_="foreignkey")
    op.drop_column("objects", "city_id")

    op.drop_constraint("cities_created_by_fkey", "cities", type_="foreignkey")
    op.drop_table("cities")
