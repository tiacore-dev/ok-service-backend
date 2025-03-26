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
    # Безопасный дроп, только если constraint существует
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'shift_report_details_shift_report_fkey'
        ) THEN
            ALTER TABLE shift_report_details
            DROP CONSTRAINT shift_report_details_shift_report_fkey;
        END IF;
    END$$;
    """)

    # Добавляем constraint с ON DELETE CASCADE
    op.create_foreign_key(
        'shift_report_details_shift_report_fkey',
        'shift_report_details',
        'shift_reports',
        ['shift_report'],
        ['shift_report_id'],
        ondelete='CASCADE'
    )


def downgrade():
    # Удаляем FK, если он есть
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'shift_report_details_shift_report_fkey'
        ) THEN
            ALTER TABLE shift_report_details
            DROP CONSTRAINT shift_report_details_shift_report_fkey;
        END IF;
    END$$;
    """)

    # Восстанавливаем без каскада
    op.create_foreign_key(
        'shift_report_details_shift_report_fkey',
        'shift_report_details',
        'shift_reports',
        ['shift_report'],
        ['shift_report_id']
    )
