"""Project in project works

Revision ID: 4cde69444b31
Revises: 7b5772803846
Create Date: 2025-02-03 12:19:54.481732

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '4cde69444b31'
down_revision: Union[str, None] = '7b5772803846'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Название таблицы
table_name = "project_works"


def upgrade():
    # Добавление нового столбца project
    op.add_column(
        table_name,
        sa.Column("project", UUID(as_uuid=True), sa.ForeignKey(
            "projects.project_id"), nullable=False)
    )


def downgrade():
    # Откат изменений
    op.drop_column(table_name, "project")
