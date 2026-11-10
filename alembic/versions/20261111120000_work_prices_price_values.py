"""Allow 0 and the -1 "unavailable" marker in work_prices.price.

Revision ID: 20261111120000
Revises: 20261110120000

Allowed values: ``price >= 0`` (payment amount, 0 means unpaid work) or exactly
``-1`` (the work is unavailable for the performer category). Values below
``-1`` and between ``-1`` and ``0`` are rejected.

The check constraint is added as ``NOT VALID``: PostgreSQL enforces it for every
new INSERT/UPDATE but does not re-check or touch rows that already exist, so
historical prices stay exactly as they are. Run
``ALTER TABLE work_prices VALIDATE CONSTRAINT check_work_prices_price_values``
manually once legacy rows are confirmed to satisfy the rule.

Also adds an index on ``(work, category)``: the price lookup used by payment
calculation and by the shift work availability check filters on these columns.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20261111120000"
down_revision: Union[str, None] = "20261110120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONSTRAINT_NAME = "check_work_prices_price_values"
INDEX_NAME = "ix_work_prices_work_category"


def upgrade() -> None:
    op.execute(
        f"ALTER TABLE work_prices ADD CONSTRAINT {CONSTRAINT_NAME} "
        "CHECK (price >= 0 OR price = -1) NOT VALID"
    )
    op.create_index(INDEX_NAME, "work_prices", ["work", "category"])


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="work_prices")
    op.drop_constraint(CONSTRAINT_NAME, "work_prices", type_="check")
