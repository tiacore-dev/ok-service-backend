"""Allow null creator for cities and set FK to SET NULL

Revision ID: c1e3f4ab2f1d
Revises: b2a78f94f3d1
Create Date: 2025-02-07 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c1e3f4ab2f1d"
down_revision: Union[str, None] = "b2a78f94f3d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE cities DROP CONSTRAINT IF EXISTS cities_created_by_fkey")
    op.execute("ALTER TABLE cities DROP CONSTRAINT IF EXISTS fk_cities_created_by")
    op.alter_column("cities", "created_by", existing_type=sa.UUID(), nullable=True)
    op.create_foreign_key(
        "cities_created_by_fkey",
        "cities",
        "users",
        ["created_by"],
        ["user_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.execute("ALTER TABLE cities DROP CONSTRAINT IF EXISTS cities_created_by_fkey")
    op.alter_column("cities", "created_by", existing_type=sa.UUID(), nullable=False)
    op.create_foreign_key(
        "cities_created_by_fkey",
        "cities",
        "users",
        ["created_by"],
        ["user_id"],
        ondelete="CASCADE",
    )
