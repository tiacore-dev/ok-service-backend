"""Add names to system settings.

Revision ID: 20261007090000
Revises: 20261006000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20261007090000"
down_revision: Union[str, None] = "20261006000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("system_settings", sa.Column("name", sa.String(), nullable=True))
    op.execute(
        "UPDATE system_settings "
        "SET name = 'Системный промпт' "
        "WHERE system_setting_id = 'system_prompt'"
    )
    op.alter_column("system_settings", "name", nullable=False)


def downgrade() -> None:
    op.drop_column("system_settings", "name")
