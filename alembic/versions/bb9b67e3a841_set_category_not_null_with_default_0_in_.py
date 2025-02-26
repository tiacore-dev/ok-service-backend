"""Set category NOT NULL with default=0 in users

Revision ID: bb9b67e3a841
Revises: c61c88bddc69
Create Date: 2025-02-26 16:20:29.134075

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb9b67e3a841'
down_revision: Union[str, None] = 'c61c88bddc69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Определяем название таблицы
TABLE_NAME = "users"
COLUMN_NAME = "category"


def upgrade():
    """Добавляем default=0 и делаем category NOT NULL"""

    # Сначала добавляем default, но НЕ делаем NOT NULL (чтобы избежать ошибок на null-значениях)
    op.alter_column(TABLE_NAME, COLUMN_NAME,
                    existing_type=sa.Integer,
                    # Устанавливаем default=0 на уровне БД
                    server_default=sa.text("0")
                    )

    op.alter_column("work_prices", "category",
                    existing_type=sa.Integer,
                    # Устанавливаем default=0 на уровне БД
                    server_default=sa.text("0")
                    )

    # Теперь обновляем существующие NULL-значения на 0
    op.execute(
        f"UPDATE {TABLE_NAME} SET {COLUMN_NAME} = 0 WHERE {COLUMN_NAME} IS NULL")

    # Делаем колонку NOT NULL
    op.alter_column(TABLE_NAME, COLUMN_NAME,
                    existing_type=sa.Integer,
                    nullable=False
                    )


def downgrade():
    """Откатываем изменения: снова разрешаем NULL и убираем default"""

    # Разрешаем NULL обратно
    op.alter_column(TABLE_NAME, COLUMN_NAME,
                    existing_type=sa.Integer,
                    nullable=True
                    )

    # Убираем default
    op.alter_column(TABLE_NAME, COLUMN_NAME,
                    existing_type=sa.Integer,
                    server_default=None
                    )

    op.alter_column("work_prices", "category",
                    existing_type=sa.Integer,
                    server_default=None
                    )
