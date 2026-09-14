"""add specification status

Revision ID: 20260831120000
Revises: 20260828100000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260831120000"
down_revision: Union[str, None] = "20260828100000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("status", sa.String(length=32), nullable=True),
    )
    op.execute("UPDATE projects SET status = 'in_progress' WHERE status IS NULL")
    op.alter_column("projects", "status", nullable=False)
    op.create_check_constraint(
        "check_projects_status",
        "projects",
        "status IN ('pending', 'in_progress', 'works_completed', 'closed')",
    )


def downgrade() -> None:
    op.drop_constraint("check_projects_status", "projects", type_="check")
    op.drop_column("projects", "status")
