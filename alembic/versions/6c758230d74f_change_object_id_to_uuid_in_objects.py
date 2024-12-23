from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = '6c758230d74f'
down_revision = '550e12fff8ce'
branch_labels = None
depends_on = None


def upgrade():
    # Удаляем старые внешние ключи
    op.drop_constraint('projects_object_id_fkey',
                       'projects', type_='foreignkey')

    # Переименование столбцов для согласованности именования
    op.alter_column('objects', 'object_id',
                    new_column_name='object', existing_type=sa.String)
    op.alter_column('projects', 'object_id',
                    new_column_name='object', existing_type=sa.String)

    # Меняем тип столбца object в таблице objects
    op.alter_column(
        'objects',
        'object',
        type_=UUID(as_uuid=True),
        existing_type=sa.String,
        nullable=False,
        postgresql_using="object::uuid"
    )

    # Меняем тип столбца object в таблице projects
    op.alter_column(
        'projects',
        'object',
        type_=UUID(as_uuid=True),
        existing_type=sa.String,
        nullable=False,
        postgresql_using="object::uuid"
    )

    # Повторно создаем внешний ключ для projects.object
    op.create_foreign_key(
        'projects_object_fkey', 'projects', 'objects',
        ['object'], ['object']
    )


def downgrade():
    # Удаляем внешний ключ
    op.drop_constraint('projects_object_fkey', 'projects', type_='foreignkey')

    # Возвращаем старые имена столбцов
    op.alter_column('objects', 'object', new_column_name='object_id',
                    existing_type=UUID(as_uuid=True))
    op.alter_column('projects', 'object', new_column_name='object_id',
                    existing_type=UUID(as_uuid=True))

    # Возвращаем типы столбцов
    op.alter_column(
        'objects',
        'object_id',
        type_=sa.String,
        existing_type=UUID(as_uuid=True),
        nullable=False,
        postgresql_using="object::text"
    )
    op.alter_column(
        'projects',
        'object_id',
        type_=sa.String,
        existing_type=UUID(as_uuid=True),
        nullable=False,
        postgresql_using="object::text"
    )

    # Восстанавливаем внешний ключ
    op.create_foreign_key(
        'projects_object_id_fkey', 'projects', 'objects',
        ['object_id'], ['object_id']
    )
