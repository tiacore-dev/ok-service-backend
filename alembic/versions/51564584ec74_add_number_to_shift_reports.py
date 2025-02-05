"""Add number to shift_reports

Revision ID: 51564584ec74
Revises: 35c1fa470707
Create Date: 2025-02-02 15:05:08.412622

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51564584ec74'
down_revision: Union[str, None] = '35c1fa470707'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Добавляем `DEFAULT 0` для колонки `number`"""
    op.alter_column(
        'shift_reports',  # Таблица
        'number',  # Поле
        existing_type=sa.Integer(),
        nullable=False,
        server_default=sa.text("0")  # Добавляем значение по умолчанию
    )

    # Обновляем существующие NULL-значения, если они есть
    op.execute("UPDATE shift_reports SET number = 0 WHERE number IS NULL")


def downgrade():
    """Откатываем изменения"""
    op.alter_column(
        'shift_reports',
        'number',
        existing_type=sa.Integer(),
        nullable=False,
        server_default=None  # Убираем `DEFAULT 0`
    )
