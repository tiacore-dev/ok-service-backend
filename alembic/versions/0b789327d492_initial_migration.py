"""Initial migration

Revision ID: 0b789327d492
Revises: 
Create Date: 2025-01-17 18:34:18.187770

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, NUMERIC
from uuid import uuid4


# revision identifiers, used by Alembic.
revision: str = '0b789327d492'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # ### creating tables ###
    op.create_table(
        'logs',
        sa.Column('log_id', UUID(as_uuid=True), primary_key=True,
                  nullable=False, default=uuid4),
        sa.Column('login', sa.String, nullable=False),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('timestamp', sa.DateTime,
                  nullable=True, default=sa.func.now())
    )

    op.create_table(
        'object_statuses',
        sa.Column('object_status_id', sa.String,
                  primary_key=True, nullable=False),
        sa.Column('name', sa.String, nullable=False)
    )

    op.create_table(
        'objects',
        sa.Column('object_id', UUID(as_uuid=True),
                  primary_key=True, nullable=False, default=uuid4),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('address', sa.String, nullable=True),
        sa.Column('description', sa.String, nullable=True),
        sa.Column('status', sa.String, sa.ForeignKey(
            'object_statuses.object_status_id'), nullable=True),
        sa.Column('deleted', sa.Boolean, nullable=False, default=False)
    )

    op.create_table(
        'roles',
        sa.Column('role_id', sa.String, primary_key=True, nullable=False),
        sa.Column('name', sa.String, nullable=False)
    )

    op.create_table(
        'users',
        sa.Column('user_id', UUID(as_uuid=True), primary_key=True,
                  nullable=False, default=uuid4),
        sa.Column('login', sa.String, nullable=False),
        sa.Column('password_hash', sa.String, nullable=False),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('role', sa.String, sa.ForeignKey(
            'roles.role_id'), nullable=False),
        sa.Column('category', sa.Integer, nullable=True),
        sa.Column('deleted', sa.Boolean, nullable=False, default=False)
    )

    op.create_table(
        'projects',
        sa.Column('project_id', UUID(as_uuid=True),
                  primary_key=True, nullable=False, default=uuid4),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('object', UUID(as_uuid=True), sa.ForeignKey(
            'objects.object_id'), nullable=False),
        sa.Column('project_leader', UUID(as_uuid=True),
                  sa.ForeignKey('users.user_id'), nullable=True),
        sa.Column('deleted', sa.Boolean, nullable=False, default=False)
    )

    op.create_table(
        'work_categories',
        sa.Column('work_category_id', UUID(as_uuid=True),
                  primary_key=True, nullable=False, default=uuid4),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('deleted', sa.Boolean, nullable=False, default=False)
    )

    op.create_table(
        'works',
        sa.Column('work_id', UUID(as_uuid=True), primary_key=True,
                  nullable=False, default=uuid4),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('category', UUID(as_uuid=True), sa.ForeignKey(
            'work_categories.work_category_id'), nullable=True),
        sa.Column('measurement_unit', sa.String, nullable=True),
        sa.Column('deleted', sa.Boolean, nullable=False, default=False)
    )

    op.create_table(
        'project_works',
        sa.Column('project_work_id', UUID(as_uuid=True),
                  primary_key=True, nullable=False, default=uuid4),
        sa.Column('work', UUID(as_uuid=True), sa.ForeignKey(
            'works.work_id'), nullable=False),
        sa.Column('quantity', NUMERIC(
            precision=10, scale=2), nullable=False),
        sa.Column('summ', NUMERIC(precision=10, scale=2), nullable=True),
        sa.Column('signed', sa.Boolean, nullable=False, default=False)
    )

    op.create_table(
        'work_prices',
        sa.Column('work_price_id', UUID(as_uuid=True),
                  primary_key=True, nullable=False, default=uuid4),
        sa.Column('work', UUID(as_uuid=True), sa.ForeignKey('works.work_id')),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('category', sa.Integer, nullable=False),
        sa.Column('price', NUMERIC(precision=10, scale=2), nullable=False),
        sa.Column('deleted', sa.Boolean, nullable=False, default=False)
    )

    op.create_table(
        'project_schedules',
        sa.Column('project_schedule_id', UUID(as_uuid=True),
                  primary_key=True, nullable=False, default=uuid4),
        sa.Column('work', UUID(as_uuid=True), sa.ForeignKey(
            'works.work_id'), nullable=False),
        sa.Column('quantity', NUMERIC(precision=10, scale=2), nullable=False),
        sa.Column('date', sa.Integer, nullable=True)
    )

    op.create_table(
        'shift_reports',
        sa.Column('shift_report_id', UUID(as_uuid=True),
                  primary_key=True, nullable=False, default=uuid4),
        sa.Column('user', UUID(as_uuid=True), sa.ForeignKey(
            'users.user_id'), nullable=False),
        sa.Column('date', sa.Integer, nullable=False),
        sa.Column('project', UUID(as_uuid=True), sa.ForeignKey(
            'projects.project_id'), nullable=False),
        sa.Column('signed', sa.Boolean, nullable=False, default=False),
        sa.Column('deleted', sa.Boolean, nullable=False, default=False)
    )

    op.create_table(
        'shift_report_details',
        sa.Column('shift_report_details_id', UUID(as_uuid=True),
                  primary_key=True, nullable=False, default=uuid4),
        sa.Column('shift_report', UUID(as_uuid=True), sa.ForeignKey(
            'shift_reports.shift_report_id'), nullable=False),
        sa.Column('work', UUID(as_uuid=True), sa.ForeignKey(
            'works.work_id'), nullable=False),
        sa.Column('quantity', NUMERIC(precision=10, scale=2), nullable=False),
        sa.Column('summ', NUMERIC(precision=10, scale=2), nullable=False)
    )


def downgrade():
    # ### dropping tables ###
    op.drop_table('works')
    op.drop_table('work_prices')
    op.drop_table('work_categories')
    op.drop_table('users')
    op.drop_table('shift_reports')
    op.drop_table('shift_report_details')
    op.drop_table('roles')
    op.drop_table('projects')
    op.drop_table('project_works')
    op.drop_table('project_schedules')
    op.drop_table('objects')
    op.drop_table('object_statuses')
    op.drop_table('logs')
