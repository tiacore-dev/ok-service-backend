"""add work plans

Revision ID: 20260831130000
Revises: 20260831120000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260831130000"
down_revision: Union[str, None] = "20260831120000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "work_plans",
        sa.Column("work_plan_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("summ", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("work_plan_id"),
        sa.CheckConstraint("EXTRACT(DAY FROM date) = 1", name="check_work_plans_first_day"),
        sa.CheckConstraint("summ >= 0", name="check_work_plans_summ_non_negative"),
    )
    op.create_index(
        "uq_work_plans_active_date_user",
        "work_plans",
        ["date", "user_id"],
        unique=True,
        postgresql_where=sa.text("deleted = false AND user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_work_plans_active_company_date",
        "work_plans",
        ["date"],
        unique=True,
        postgresql_where=sa.text("deleted = false AND user_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_work_plans_active_company_date", table_name="work_plans")
    op.drop_index("uq_work_plans_active_date_user", table_name="work_plans")
    op.drop_table("work_plans")
