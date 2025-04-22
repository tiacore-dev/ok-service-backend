"""add relation between shift_report_details and project_works

Revision ID: eb309edeb3fc
Revises: 8c8cd5edc8fe
Create Date: 2025-04-17 14:47:17.053045

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb309edeb3fc'
down_revision: Union[str, None] = '8c8cd5edc8fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('shift_report_details',
                  sa.Column('project_work', sa.UUID(), nullable=True)
                  )
    op.create_foreign_key(
        'fk_shift_report_details_project_work',
        'shift_report_details',
        'project_works',
        ['project_work'],
        ['project_work_id'],
        ondelete='SET NULL'
    )


def downgrade():
    op.drop_constraint(
        'fk_shift_report_details_project_work',
        'shift_report_details',
        type_='foreignkey'
    )
    op.drop_column('shift_report_details', 'project_work')
