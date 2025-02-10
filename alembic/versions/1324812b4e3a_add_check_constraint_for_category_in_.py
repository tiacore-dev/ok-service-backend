"""Add check constraint for category in users and work prices

Revision ID: 1324812b4e3a
Revises: 0c0962548f54
Create Date: 2025-02-10 17:09:22.175879

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1324812b4e3a'
down_revision: Union[str, None] = '0c0962548f54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Добавление ограничения на значения category
    op.create_check_constraint(
        "check_category_values",
        "users",
        "category IN (0, 1, 2, 3, 4)"
    )

    op.create_check_constraint(
        "check_price_category_values",
        "work_prices",
        "category IN (0, 1, 2, 3, 4)"
    )


def downgrade():
    # Удаление ограничения при откате миграции
    op.drop_constraint("check_category_values", "users", type_="check")
    op.drop_constraint("check_price_category_values", "work_prices", type_="check")