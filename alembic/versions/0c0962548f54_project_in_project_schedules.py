"""Project in project schedules

Revision ID: 0c0962548f54
Revises: 80c660146186
Create Date: 2025-02-07 12:26:22.399671

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '0c0962548f54'
down_revision: Union[str, None] = '80c660146186'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Добавление нового столбца project
    op.add_column(
        "project_schedules",
        sa.Column("project", UUID(as_uuid=True), sa.ForeignKey(
            "projects.project_id"), nullable=False)
    )


def downgrade():
    # Откат изменений
    op.drop_column("project_schedules", "project")
