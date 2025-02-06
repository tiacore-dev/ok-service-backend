"""Other created at and by

Revision ID: f0bed8fba6e4
Revises: 465206ef39bc
Create Date: 2025-02-06 15:47:12.491894

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0bed8fba6e4'
down_revision: Union[str, None] = '465206ef39bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем новый столбец с типом Integer и default значением в формате timestamp
    op.add_column("project_schedules", sa.Column(
        'created_at', sa.Integer(), server_default=sa.text("EXTRACT(EPOCH FROM NOW())"), nullable=False
    ))
    # Добавляем новый столбец created_by
    op.add_column('project_schedules', sa.Column(
        'created_by', sa.UUID(), nullable=False))

    # Добавляем ForeignKey (FK) на users.user_id
    op.create_foreign_key(
        'fk_project_schedules_created_by',  # Название FK
        'project_schedules', 'users',  # Таблица-источник и таблица-цель
        ['created_by'], ['user_id'],  # Поля для связи
        ondelete='CASCADE'  # Можно менять на 'CASCADE', если требуется
    )

    # Добавляем новый столбец с типом Integer и default значением в формате timestamp
    op.add_column("project_works", sa.Column(
        'created_at', sa.Integer(), server_default=sa.text("EXTRACT(EPOCH FROM NOW())"), nullable=False
    ))
    # Добавляем новый столбец created_by
    op.add_column('project_works', sa.Column(
        'created_by', sa.UUID(), nullable=False))

    # Добавляем ForeignKey (FK) на users.user_id
    op.create_foreign_key(
        'fk_project_works_created_by',  # Название FK
        'project_works', 'users',  # Таблица-источник и таблица-цель
        ['created_by'], ['user_id'],  # Поля для связи
        ondelete='CASCADE'  # Можно менять на 'CASCADE', если требуется
    )

    # Добавляем новый столбец с типом Integer и default значением в формате timestamp
    op.add_column("shift_report_details", sa.Column(
        'created_at', sa.Integer(), server_default=sa.text("EXTRACT(EPOCH FROM NOW())"), nullable=False
    ))
    # Добавляем новый столбец created_by
    op.add_column('shift_report_details', sa.Column(
        'created_by', sa.UUID(), nullable=False))

    # Добавляем ForeignKey (FK) на users.user_id
    op.create_foreign_key(
        'fk_shift_report_details_created_by',  # Название FK
        'shift_report_details', 'users',  # Таблица-источник и таблица-цель
        ['created_by'], ['user_id'],  # Поля для связи
        ondelete='CASCADE'  # Можно менять на 'CASCADE', если требуется
    )

    # Добавляем новый столбец с типом Integer и default значением в формате timestamp
    op.add_column("shift_reports", sa.Column(
        'created_at', sa.Integer(), server_default=sa.text("EXTRACT(EPOCH FROM NOW())"), nullable=False
    ))
    # Добавляем новый столбец created_by
    op.add_column('shift_reports', sa.Column(
        'created_by', sa.UUID(), nullable=False))

    # Добавляем ForeignKey (FK) на users.user_id
    op.create_foreign_key(
        'fk_shift_reports_created_by',  # Название FK
        'shift_reports', 'users',  # Таблица-источник и таблица-цель
        ['created_by'], ['user_id'],  # Поля для связи
        ondelete='CASCADE'  # Можно менять на 'CASCADE', если требуется
    )

    # Добавляем новый столбец с типом Integer и default значением в формате timestamp
    op.add_column("work_categories", sa.Column(
        'created_at', sa.Integer(), server_default=sa.text("EXTRACT(EPOCH FROM NOW())"), nullable=False
    ))
    # Добавляем новый столбец created_by
    op.add_column('work_categories', sa.Column(
        'created_by', sa.UUID(), nullable=False))

    # Добавляем ForeignKey (FK) на users.user_id
    op.create_foreign_key(
        'fk_work_categories_created_by',  # Название FK
        'work_categories', 'users',  # Таблица-источник и таблица-цель
        ['created_by'], ['user_id'],  # Поля для связи
        ondelete='CASCADE'  # Можно менять на 'CASCADE', если требуется
    )

    # Добавляем новый столбец с типом Integer и default значением в формате timestamp
    op.add_column("work_prices", sa.Column(
        'created_at', sa.Integer(), server_default=sa.text("EXTRACT(EPOCH FROM NOW())"), nullable=False
    ))
    # Добавляем новый столбец created_by
    op.add_column('work_prices', sa.Column(
        'created_by', sa.UUID(), nullable=False))

    # Добавляем ForeignKey (FK) на users.user_id
    op.create_foreign_key(
        'fk_work_prices_created_by',  # Название FK
        'work_prices', 'users',  # Таблица-источник и таблица-цель
        ['created_by'], ['user_id'],  # Поля для связи
        ondelete='CASCADE'  # Можно менять на 'CASCADE', если требуется
    )

    # Добавляем новый столбец с типом Integer и default значением в формате timestamp
    op.add_column("works", sa.Column(
        'created_at', sa.Integer(), server_default=sa.text("EXTRACT(EPOCH FROM NOW())"), nullable=False
    ))
    # Добавляем новый столбец created_by
    op.add_column('works', sa.Column(
        'created_by', sa.UUID(), nullable=False))

    # Добавляем ForeignKey (FK) на users.user_id
    op.create_foreign_key(
        'fk_works_created_by',  # Название FK
        'works', 'users',  # Таблица-источник и таблица-цель
        ['created_by'], ['user_id'],  # Поля для связи
        ondelete='CASCADE'  # Можно менять на 'CASCADE', если требуется
    )


def downgrade() -> None:
    # Удаляем новый столбец
    op.drop_column("project_schedules", 'created_at')
    # Удаляем ForeignKey
    op.drop_constraint('fk_project_schedules_created_by',
                       'project_schedules', type_='foreignkey')

    # Удаляем столбец created_by
    op.drop_column('project_schedules', 'created_by')

    # Удаляем новый столбец
    op.drop_column("project_works", 'created_at')
    # Удаляем ForeignKey
    op.drop_constraint('fk_project_works_created_by',
                       'project_works', type_='foreignkey')

    # Удаляем столбец created_by
    op.drop_column('project_works', 'created_by')

    # Удаляем новый столбец
    op.drop_column("shift_report_details", 'created_at')
    # Удаляем ForeignKey
    op.drop_constraint('fk_shift_report_details_created_by',
                       'shift_report_details', type_='foreignkey')

    # Удаляем столбец created_by
    op.drop_column('shift_report_details', 'created_by')

    # Удаляем новый столбец
    op.drop_column("shift_reports", 'created_at')
    # Удаляем ForeignKey
    op.drop_constraint('fk_shift_reports_created_by',
                       'shift_reports', type_='foreignkey')

    # Удаляем столбец created_by
    op.drop_column('shift_reports', 'created_by')

    # Удаляем новый столбец
    op.drop_column("work_categories", 'created_at')
    # Удаляем ForeignKey
    op.drop_constraint('fk_work_categories_created_by',
                       'work_categories', type_='foreignkey')

    # Удаляем столбец created_by
    op.drop_column('work_categories', 'created_by')

    # Удаляем новый столбец
    op.drop_column("work_prices", 'created_at')
    # Удаляем ForeignKey
    op.drop_constraint('fk_work_prices_created_by',
                       'work_prices', type_='foreignkey')

    # Удаляем столбец created_by
    op.drop_column('work_prices', 'created_by')

    # Удаляем новый столбец
    op.drop_column("works", 'created_at')
    # Удаляем ForeignKey
    op.drop_constraint('fk_works_created_by',
                       'works', type_='foreignkey')

    # Удаляем столбец created_by
    op.drop_column('works', 'created_by')
