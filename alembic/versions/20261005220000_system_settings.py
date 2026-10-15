"""Add system settings reference and the system prompt setting."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20261005220000"
down_revision: Union[str, None] = "20261005210000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("system_setting_id", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("modified_at", sa.BigInteger(), nullable=True),
        sa.Column("modified_by", sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint("system_setting_id"),
        sa.ForeignKeyConstraint(["modified_by"], ["users.user_id"]),
    )
def downgrade() -> None:
    op.drop_table("system_settings")
