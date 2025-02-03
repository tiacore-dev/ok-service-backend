"""Shift report detaul id

Revision ID: 7b5772803846
Revises: 8bbb9dfcec1b
Create Date: 2025-02-03 12:07:54.388595

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '7b5772803846'
down_revision: Union[str, None] = '8bbb9dfcec1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Название таблицы
table_name = "shift_report_details"
old_column_name = "shift_report_details_id"
new_column_name = "shift_report_detail_id"


def upgrade():
    # Удаление первичного ключа
    op.drop_constraint(f"{table_name}_pkey", table_name, type_="primary")

    # Переименование столбца
    op.alter_column(
        table_name,
        old_column_name,
        new_column_name=new_column_name,
        existing_type=UUID(as_uuid=True),
    )
    # Восстановление первичного ключа
    op.create_primary_key(f"{table_name}_pkey", table_name, [new_column_name])


def downgrade():
    # Откат: Удаляем новый ключ
    op.drop_constraint(f"{table_name}_pkey", table_name, type_="primary")

    # Переименовываем обратно
    op.alter_column(
        table_name,
        new_column_name,
        new_column_name=old_column_name,
        existing_type=UUID(as_uuid=True),
    )

    # Восстанавливаем старый первичный ключ
    op.create_primary_key(f"{table_name}_pkey", table_name, [old_column_name])
