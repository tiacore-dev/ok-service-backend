"""Created at, manager in objects, created by, parameters of work

Revision ID: 448b72e134b7
Revises: cce9815f1913
Create Date: 2025-02-05 18:38:38.969655

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from uuid import UUID


# revision identifiers, used by Alembic.
revision: str = '448b72e134b7'
down_revision: Union[str, None] = 'cce9815f1913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Добавление нового столбца project
    op.add_column(
        "objects",
        sa.Column("manager", sa.UUID(), sa.ForeignKey(
            "users.user_id"), nullable=False)
    )
    # Добавляем новый столбец с типом Integer и default значением в формате timestamp
    op.add_column("objects", sa.Column(
        'created_at', sa.Integer(), server_default=sa.text("EXTRACT(EPOCH FROM NOW())"), nullable=True
    ))
    # Добавляем новый столбец created_by
    op.add_column('objects', sa.Column(
        'created_by', sa.UUID(), nullable=True))

    # Добавляем ForeignKey (FK) на users.user_id
    op.create_foreign_key(
        'fk_objects_created_by',  # Название FK
        'objects', 'users',  # Таблица-источник и таблица-цель
        ['created_by'], ['user_id'],  # Поля для связи
        ondelete='CASCADE'  # Можно менять на 'CASCADE', если требуется
    )

    # Добавляем новый столбец с типом Integer и default значением в формате timestamp
    op.add_column("projects", sa.Column(
        'created_at', sa.Integer(), server_default=sa.text("EXTRACT(EPOCH FROM NOW())"), nullable=True
    ))
    # Добавляем новый столбец created_by
    op.add_column('projects', sa.Column(
        'created_by', sa.UUID(), nullable=True))

    # Добавляем ForeignKey (FK) на users.user_id
    op.create_foreign_key(
        'fk_projects_created_by',  # Название FK
        'projects', 'users',  # Таблица-источник и таблица-цель
        ['created_by'], ['user_id'],  # Поля для связи
        ondelete='CASCADE'  # Можно менять на 'CASCADE', если требуется
    )

    op.add_column('projects', sa.Column(
        'night_shift_available', sa.Boolean, nullable=False, default=False))
    op.add_column('projects', sa.Column(
        'extreme_conditions_available', sa.Boolean, nullable=False, default=False))


def downgrade():
    # Откат изменений
    op.drop_column("objects", "manager")
    # Удаляем новый столбец
    op.drop_column("objects", 'created_at')
    # Удаляем ForeignKey
    op.drop_constraint('fk_objects_created_by',
                       'objects', type_='foreignkey')

    # Удаляем столбец created_by
    op.drop_column('objects', 'created_by')
    # Удаляем новый столбец
    op.drop_column("projects", 'created_at')
    # Удаляем ForeignKey
    op.drop_constraint('fk_projects_created_by',
                       'projects', type_='foreignkey')

    # Удаляем столбец created_by
    op.drop_column('projects', 'created_by')

    op.drop_column('projects', 'night_shift_available')
    op.drop_column('projects', 'extreme_conditions_available')
