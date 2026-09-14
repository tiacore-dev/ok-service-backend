"""add acceptances and work acceptance relations

Revision ID: 20260827150000
Revises: 20260827120000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260827150000"
down_revision: Union[str, None] = "20260827120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "acceptances",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("date", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("comment", sa.String(), nullable=True),
        sa.CheckConstraint(
            "status IN ('presented', 'violations_found', 'accepted_on_site', 'documents_signed')",
            name="check_acceptances_status",
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.project_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "work_acceptance_relations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("acceptance_id", sa.UUID(), nullable=False),
        sa.Column("work_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["acceptance_id"], ["acceptances.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_id"], ["works.work_id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("work_acceptance_relations")
    op.drop_table("acceptances")
