"""Created at and by

Revision ID: 465206ef39bc
Revises: 448b72e134b7
Create Date: 2025-02-06 14:11:15.115056

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '465206ef39bc'
down_revision: Union[str, None] = '448b72e134b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем новый столбец с типом Integer и default значением в формате timestamp
    op.add_column("users", sa.Column(
        'created_at', sa.Integer(), server_default=sa.text("EXTRACT(EPOCH FROM NOW())"), nullable=False
    ))
    # Добавляем новый столбец created_by
    op.add_column('users', sa.Column(
        'created_by', sa.UUID(), nullable=False))

    # Добавляем ForeignKey (FK) на users.user_id
    op.create_foreign_key(
        'fk_users_created_by',  # Название FK
        'users', 'users',  # Таблица-источник и таблица-цель
        ['created_by'], ['user_id'],  # Поля для связи
        ondelete='CASCADE'  # Можно менять на 'CASCADE', если требуется
    )


def downgrade() -> None:
    # Удаляем новый столбец
    op.drop_column("users", 'created_at')
    # Удаляем ForeignKey
    op.drop_constraint('fk_users_created_by',
                       'users', type_='foreignkey')

    # Удаляем столбец created_by
    op.drop_column('users', 'created_by')
