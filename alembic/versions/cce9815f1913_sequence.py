"""Sequence

Revision ID: cce9815f1913
Revises: d8d0ca70cfc1
Create Date: 2025-02-05 13:52:20.660646

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cce9815f1913'
down_revision: Union[str, None] = 'd8d0ca70cfc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    """Создаем SEQUENCE и обновляем колонку number"""
    # Создаем SEQUENCE, если он не существует
    op.execute(
        "CREATE SEQUENCE IF NOT EXISTS shift_reports_number_seq START WITH 1 INCREMENT BY 1;")

    # Применяем SEQUENCE к колонке `number`
    op.alter_column(
        'shift_reports',
        'number',
        existing_type=sa.Integer(),
        nullable=False,
        server_default=sa.text("nextval('shift_reports_number_seq')")
    )

    # Обновляем NULL-значения в существующих данных
    op.execute(
        "UPDATE shift_reports SET number = nextval('shift_reports_number_seq') WHERE number IS NULL;")


def downgrade():
    """Откат миграции: убираем SEQUENCE"""
    op.alter_column(
        'shift_reports',
        'number',
        existing_type=sa.Integer(),
        nullable=False,
        server_default=None  # Убираем автоинкремент
    )

    # Отключаем SEQUENCE
    op.execute("DROP SEQUENCE IF EXISTS shift_reports_number_seq;")
