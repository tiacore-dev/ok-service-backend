"""add materials and work_material_relations tables

Revision ID: c3d4e5f6a7b8
Revises: b7c8d9e0f1a2
Create Date: 2026-02-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "materials",
        sa.Column("material_id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("measurement_unit", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
            nullable=True,
        ),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=False, default=False),
    )

    op.create_table(
        "work_material_relations",
        sa.Column(
            "work_material_relation_id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("work", UUID(as_uuid=True), sa.ForeignKey("works.work_id"), nullable=False),
        sa.Column(
            "material",
            UUID(as_uuid=True),
            sa.ForeignKey("materials.material_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
            nullable=False,
        ),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("work_material_relations")
    op.drop_table("materials")
