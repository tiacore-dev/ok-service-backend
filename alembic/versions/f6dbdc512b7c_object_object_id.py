"""object -> object_id

Revision ID: f6dbdc512b7c
Revises: 0975923f29bd
Create Date: 2025-01-17 13:04:44.789225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6dbdc512b7c'
down_revision: Union[str, None] = '0975923f29bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Удаляем старый первичный ключ
    with op.batch_alter_table('objects') as batch_op:
        batch_op.drop_constraint('objects_pkey', type_='primary')

    # Переименовываем столбец
    op.alter_column('objects', 'object',
                    new_column_name='object_id', existing_type=sa.String())

    # Назначаем новый первичный ключ
    with op.batch_alter_table('objects') as batch_op:
        batch_op.create_primary_key('objects_pkey', ['object_id'])


def downgrade():
    # Удаляем новый первичный ключ
    with op.batch_alter_table('objects') as batch_op:
        batch_op.drop_constraint('objects_pkey', type_='primary')

    # Переименовываем столбец обратно
    op.alter_column('objects', 'object_id',
                    new_column_name='object', existing_type=sa.String())

    # Восстанавливаем старый первичный ключ
    with op.batch_alter_table('objects') as batch_op:
        batch_op.create_primary_key('objects_pkey', ['object'])
