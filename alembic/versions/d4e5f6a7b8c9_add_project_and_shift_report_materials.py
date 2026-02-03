"""add project_materials and shift_report_materials tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_materials",
        sa.Column(
            "project_material_id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "project",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.project_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "material",
            UUID(as_uuid=True),
            sa.ForeignKey("materials.material_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "project_work",
            UUID(as_uuid=True),
            sa.ForeignKey("project_works.project_work_id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.user_id"),
            nullable=False,
        ),
    )

    op.create_table(
        "shift_report_materials",
        sa.Column(
            "shift_report_material_id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "shift_report",
            UUID(as_uuid=True),
            sa.ForeignKey("shift_reports.shift_report_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "material",
            UUID(as_uuid=True),
            sa.ForeignKey("materials.material_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "shift_report_detail",
            UUID(as_uuid=True),
            sa.ForeignKey("shift_report_details.shift_report_detail_id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.user_id"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("shift_report_materials")
    op.drop_table("project_materials")
