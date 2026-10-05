"""Repair shift report browser ID columns.

Revision ID: 20261006000000
Revises: 20261005230000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20261006000000"
down_revision: Union[str, None] = "20261005230000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove columns from the previously deployed JSONB implementation.
    op.execute("ALTER TABLE shift_reports DROP COLUMN IF EXISTS start_device_info")
    op.execute("ALTER TABLE shift_reports DROP COLUMN IF EXISTS finish_device_info")

    op.execute(
        "ALTER TABLE shift_reports ADD COLUMN IF NOT EXISTS start_browser_id UUID"
    )
    op.execute(
        "ALTER TABLE shift_reports ADD COLUMN IF NOT EXISTS finish_browser_id UUID"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE shift_reports "
        "DROP COLUMN IF EXISTS finish_browser_id"
    )
    op.execute(
        "ALTER TABLE shift_reports "
        "DROP COLUMN IF EXISTS start_browser_id"
    )
    op.execute(
        "ALTER TABLE shift_reports "
        "ADD COLUMN IF NOT EXISTS start_device_info JSONB"
    )
    op.execute(
        "ALTER TABLE shift_reports "
        "ADD COLUMN IF NOT EXISTS finish_device_info JSONB"
    )
