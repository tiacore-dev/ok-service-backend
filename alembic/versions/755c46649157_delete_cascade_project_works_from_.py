"""delete cascade project works from projects

Revision ID: 755c46649157
Revises: 88852ee1fb1c
Create Date: 2025-04-23 11:38:13.766875

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "755c46649157"
down_revision: Union[str, None] = "88852ee1fb1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Удалим старый внешний ключ и создадим новый с ON DELETE CASCADE
    with op.batch_alter_table("project_works") as batch_op:
        batch_op.drop_constraint("project_works_project_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "project_works_project_fkey",
            "projects",
            ["project"],
            ["project_id"],
            ondelete="CASCADE",
        )


def downgrade():
    # Откат — удалим каскадный внешний ключ и вернём обычный
    with op.batch_alter_table("project_works") as batch_op:
        batch_op.drop_constraint("project_works_project_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "project_works_project_fkey", "projects", ["project"], ["project_id"]
        )
