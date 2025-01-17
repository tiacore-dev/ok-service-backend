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
    # Удаляем внешний ключ из таблицы projects
    with op.batch_alter_table('projects') as batch_op:
        batch_op.drop_constraint('projects_object_fkey', type_='foreignkey')

    # Удаляем первичный ключ из таблицы objects
    with op.batch_alter_table('objects') as batch_op:
        batch_op.drop_constraint('objects_pkey', type_='primary')

    # Переименовываем столбец object в object_id
    op.alter_column('objects', 'object',
                    new_column_name='object_id', existing_type=sa.String())

    # Создаем новый первичный ключ
    with op.batch_alter_table('objects') as batch_op:
        batch_op.create_primary_key('objects_pkey', ['object_id'])

    # Восстанавливаем внешний ключ в таблице projects
    with op.batch_alter_table('projects') as batch_op:
        batch_op.create_foreign_key(
            'projects_object_fkey',  # Имя ограничения
            'objects',              # Ссылаемая таблица
            ['object'],             # Поле в таблице projects
            ['object_id']           # Поле в таблице objects
        )


def downgrade():
    # Удаляем внешний ключ из таблицы projects
    with op.batch_alter_table('projects') as batch_op:
        batch_op.drop_constraint('projects_object_fkey', type_='foreignkey')

    # Удаляем новый первичный ключ
    with op.batch_alter_table('objects') as batch_op:
        batch_op.drop_constraint('objects_pkey', type_='primary')

    # Переименовываем столбец обратно с object_id на object
    op.alter_column('objects', 'object_id',
                    new_column_name='object', existing_type=sa.String())

    # Восстанавливаем старый первичный ключ
    with op.batch_alter_table('objects') as batch_op:
        batch_op.create_primary_key('objects_pkey', ['object'])

    # Восстанавливаем внешний ключ в таблице projects
    with op.batch_alter_table('projects') as batch_op:
        batch_op.create_foreign_key(
            'projects_object_fkey',  # Имя ограничения
            'objects',               # Ссылаемая таблица
            ['object'],              # Поле в таблице projects
            ['object']               # Поле в таблице objects
        )
