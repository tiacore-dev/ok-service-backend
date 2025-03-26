"""Add cascade delete to shift_report_details

Revision ID: 8c8cd5edc8fe
Revises: bb9b67e3a841
Create Date: 2025-03-26 11:34:41.298620

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c8cd5edc8fe'
down_revision: Union[str, None] = 'bb9b67e3a841'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Удаляем старый внешний ключ shift_report_details → shift_reports
    op.drop_constraint(
        'shift_report_details_shift_report_fkey',
        'shift_report_details',
        type_='foreignkey'
    )
    # Создаём новый внешний ключ с ON DELETE CASCADE
    op.create_foreign_key(
        'shift_report_details_shift_report_fkey',
        'shift_report_details',
        'shift_reports',
        ['shift_report'],
        ['shift_report_id'],
        ondelete='CASCADE'
    )


def downgrade():
    # Удаляем внешний ключ с каскадом
    op.drop_constraint(
        'shift_report_details_shift_report_fkey',
        'shift_report_details',
        type_='foreignkey'
    )
    # Восстанавливаем внешний ключ без каскада
    op.create_foreign_key(
        'shift_report_details_shift_report_fkey',
        'shift_report_details',
        'shift_reports',
        ['shift_report'],
        ['shift_report_id']
    )
