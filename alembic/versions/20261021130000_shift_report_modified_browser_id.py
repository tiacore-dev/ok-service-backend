"""Store the browser UUID of the last successful shift report edit.

Revision ID: 20261021130000
Revises: 20261021120000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261021130000"
down_revision: Union[str, None] = "20261021120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shift_reports",
        sa.Column("modified_browser_id", postgresql.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("shift_reports", "modified_browser_id")
