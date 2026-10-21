"""Add optional production and penalty rates to shift standards.

Revision ID: 20261021120000
Revises: 20261019150000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20261021120000"
down_revision: Union[str, None] = "20261019150000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shift_standards", sa.Column("production_rate_rub", sa.Float(), nullable=True)
    )
    op.add_column(
        "shift_standards", sa.Column("penalty_rate_percent", sa.Float(), nullable=True)
    )
    op.create_check_constraint(
        "check_shift_standards_production_rate_rub",
        "shift_standards",
        "production_rate_rub >= 0 AND production_rate_rub < 'Infinity'::double precision",
    )
    op.create_check_constraint(
        "check_shift_standards_penalty_rate_percent",
        "shift_standards",
        "penalty_rate_percent >= 0 AND penalty_rate_percent <= 100",
    )


def downgrade() -> None:
    op.drop_constraint(
        "check_shift_standards_penalty_rate_percent", "shift_standards", type_="check"
    )
    op.drop_constraint(
        "check_shift_standards_production_rate_rub", "shift_standards", type_="check"
    )
    op.drop_column("shift_standards", "penalty_rate_percent")
    op.drop_column("shift_standards", "production_rate_rub")
