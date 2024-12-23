"""Change names, no _id

Revision ID: 0975923f29bd
Revises: 6c758230d74f
Create Date: 2024-12-23 19:02:29.862662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0975923f29bd'
down_revision: Union[str, None] = '6c758230d74f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Переименование work_id в work_prices -> work
    op.alter_column('work_prices', 'work_id', new_column_name='work')

    # Переименование work_id в project_works -> work
    op.alter_column('project_works', 'work_id', new_column_name='work')

    # Переименование work_id в project_schedules -> work
    op.alter_column('project_schedules', 'work_id', new_column_name='work')

    # Переименование work_id в shift_report_details -> work
    op.alter_column('shift_report_details', 'work_id', new_column_name='work')

    # Переименование shift_report_id в shift_report_details -> shift_report
    op.alter_column('shift_report_details', 'shift_report_id',
                    new_column_name='shift_report')

    # Переименование project_id в shift_reports -> project
    op.alter_column('shift_reports', 'project_id', new_column_name='project')

    # Переименование user_id в shift_reports -> user
    op.alter_column('shift_reports', 'user_id', new_column_name='user')


def downgrade() -> None:
    # Возврат изменений в downgrade
    op.alter_column('work_prices', 'work', new_column_name='work_id')
    op.alter_column('project_works', 'work', new_column_name='work_id')
    op.alter_column('project_schedules', 'work', new_column_name='work_id')
    op.alter_column('shift_report_details', 'work', new_column_name='work_id')
    op.alter_column('shift_report_details', 'shift_report',
                    new_column_name='shift_report_id')
    op.alter_column('shift_reports', 'project', new_column_name='project_id')
    op.alter_column('shift_reports', 'user', new_column_name='user_id')
