"""Add project-place and shift-place relations.

Revision ID: 20260811_place_relations
Revises: 20260811_places
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260811_place_relations"
down_revision: Union[str, None] = "20260811_places"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_place_relations",
        sa.Column("project_place_relation_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("place_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"]),
        sa.ForeignKeyConstraint(["place_id"], ["places.place_id"]),
        sa.PrimaryKeyConstraint("project_place_relation_id"),
        sa.UniqueConstraint(
            "project_id", "place_id", name="uq_project_place_relations"
        ),
    )
    op.create_table(
        "shift_place_relations",
        sa.Column("shift_place_relation_id", sa.UUID(), nullable=False),
        sa.Column("shift_report_id", sa.UUID(), nullable=False),
        sa.Column("place_id", sa.UUID(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["shift_report_id"], ["shift_reports.shift_report_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["place_id"], ["places.place_id"]),
        sa.PrimaryKeyConstraint("shift_place_relation_id"),
        sa.UniqueConstraint(
            "shift_report_id", "place_id", name="uq_shift_place_relations"
        ),
    )


def downgrade() -> None:
    op.drop_table("shift_place_relations")
    op.drop_table("project_place_relations")
