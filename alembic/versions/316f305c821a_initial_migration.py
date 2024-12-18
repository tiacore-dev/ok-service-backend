"""Initial migration

Revision ID: 316f305c821a
Revises: 
Create Date: 2024-12-17 16:37:58.217169

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '316f305c821a'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаём таблицы без зависимостей
    op.create_table('roles',
                    sa.Column('role_id', sa.VARCHAR(), nullable=False),
                    sa.Column('name', sa.VARCHAR(), nullable=False),
                    sa.PrimaryKeyConstraint('role_id', name='roles_pkey')
                    )

    op.create_table('users',
                    sa.Column('user_id', sa.UUID(), nullable=False),
                    sa.Column('login', sa.VARCHAR(), nullable=False),
                    sa.Column('password_hash', sa.VARCHAR(), nullable=False),
                    sa.Column('name', sa.VARCHAR(), nullable=False),
                    sa.Column('category', sa.INTEGER(), nullable=True),
                    sa.Column('deleted', sa.BOOLEAN(), nullable=False),
                    sa.PrimaryKeyConstraint('user_id', name='users_pkey'),
                    postgresql_ignore_search_path=False
                    )

    op.create_table('object_statuses',
                    sa.Column('object_status_id',
                              sa.VARCHAR(), nullable=False),
                    sa.Column('name', sa.VARCHAR(), nullable=False),
                    sa.PrimaryKeyConstraint(
                        'object_status_id', name='object_statuses_pkey'),
                    postgresql_ignore_search_path=False
                    )

    op.create_table('work_categories',
                    sa.Column('work_category_id', sa.UUID(), nullable=False),
                    sa.Column('name', sa.VARCHAR(), nullable=False),
                    sa.Column('deleted', sa.BOOLEAN(), nullable=False),
                    sa.PrimaryKeyConstraint(
                        'work_category_id', name='work_categories_pkey'),
                    postgresql_ignore_search_path=False
                    )

    # works зависит от work_categories
    op.create_table('works',
                    sa.Column('work_id', sa.UUID(), nullable=False),
                    sa.Column('name', sa.VARCHAR(), nullable=False),
                    sa.Column('category', sa.UUID(), nullable=True),
                    sa.Column('measurement_unit', sa.VARCHAR(), nullable=True),
                    sa.Column('deleted', sa.BOOLEAN(), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['category'], ['work_categories.work_category_id'], name='works_category_fkey'),
                    sa.PrimaryKeyConstraint('work_id', name='works_pkey'),
                    postgresql_ignore_search_path=False
                    )

    # objects зависит от object_statuses
    op.create_table('objects',
                    sa.Column('object_id', sa.VARCHAR(), nullable=False),
                    sa.Column('name', sa.VARCHAR(), nullable=False),
                    sa.Column('address', sa.VARCHAR(), nullable=True),
                    sa.Column('description', sa.VARCHAR(), nullable=True),
                    sa.Column('status', sa.VARCHAR(), nullable=True),
                    sa.Column('deleted', sa.BOOLEAN(), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['status'], ['object_statuses.object_status_id'], name='objects_status_fkey'),
                    sa.PrimaryKeyConstraint('object_id', name='objects_pkey'),
                    postgresql_ignore_search_path=False
                    )

    # projects зависит от objects и users
    op.create_table('projects',
                    sa.Column('project_id', sa.UUID(), nullable=False),
                    sa.Column('name', sa.VARCHAR(), nullable=False),
                    sa.Column('object_id', sa.VARCHAR(), nullable=False),
                    sa.Column('project_leader', sa.UUID(), nullable=True),
                    sa.Column('deleted', sa.BOOLEAN(), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['object_id'], ['objects.object_id'], name='projects_object_id_fkey'),
                    sa.ForeignKeyConstraint(['project_leader'], [
                        'users.user_id'], name='projects_project_leader_fkey'),
                    sa.PrimaryKeyConstraint(
                        'project_id', name='projects_pkey'),
                    postgresql_ignore_search_path=False
                    )

    # shift_reports зависит от projects и users
    op.create_table('shift_reports',
                    sa.Column('shift_report_id', sa.UUID(), nullable=False),
                    sa.Column('user_id', sa.UUID(), nullable=False),
                    sa.Column('date', sa.INTEGER(), nullable=False),
                    sa.Column('project_id', sa.UUID(), nullable=False),
                    sa.Column('signed', sa.BOOLEAN(), nullable=False),
                    sa.Column('deleted', sa.BOOLEAN(), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['project_id'], ['projects.project_id'], name='shift_reports_project_id_fkey'),
                    sa.ForeignKeyConstraint(
                        ['user_id'], ['users.user_id'], name='shift_reports_user_id_fkey'),
                    sa.PrimaryKeyConstraint(
                        'shift_report_id', name='shift_reports_pkey'),
                    postgresql_ignore_search_path=False
                    )

    # shift_report_details зависит от shift_reports и works
    op.create_table('shift_report_details',
                    sa.Column('shift_report_details_id',
                              sa.UUID(), nullable=False),
                    sa.Column('shift_report_id', sa.UUID(), nullable=False),
                    sa.Column('work_id', sa.UUID(), nullable=False),
                    sa.Column('quantity', sa.NUMERIC(
                        precision=10, scale=2), nullable=False),
                    sa.Column('summ', sa.NUMERIC(
                        precision=10, scale=2), nullable=False),
                    sa.ForeignKeyConstraint(['shift_report_id'], [
                        'shift_reports.shift_report_id'], name='shift_report_details_shift_report_id_fkey'),
                    sa.ForeignKeyConstraint(
                        ['work_id'], ['works.work_id'], name='shift_report_details_work_id_fkey'),
                    sa.PrimaryKeyConstraint('shift_report_details_id',
                                            name='shift_report_details_pkey')
                    )

    # project_works зависит от works
    op.create_table('project_works',
                    sa.Column('project_work_id', sa.UUID(), nullable=False),
                    sa.Column('work_id', sa.UUID(), nullable=False),
                    sa.Column('quantity', sa.NUMERIC(
                        precision=10, scale=2), nullable=False),
                    sa.Column('summ', sa.NUMERIC(
                        precision=10, scale=2), nullable=True),
                    sa.Column('signed', sa.BOOLEAN(), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['work_id'], ['works.work_id'], name='project_works_work_id_fkey'),
                    sa.PrimaryKeyConstraint(
                        'project_work_id', name='project_works_pkey')
                    )

    # project_schedules зависит от works
    op.create_table('project_schedules',
                    sa.Column('project_schedule_id',
                              sa.UUID(), nullable=False),
                    sa.Column('work_id', sa.UUID(), nullable=False),
                    sa.Column('quantity', sa.NUMERIC(
                        precision=10, scale=2), nullable=False),
                    sa.Column('date', sa.INTEGER(), nullable=True),
                    sa.ForeignKeyConstraint(
                        ['work_id'], ['works.work_id'], name='project_schedules_work_id_fkey'),
                    sa.PrimaryKeyConstraint('project_schedule_id',
                                            name='project_schedules_pkey')
                    )

    # work_prices зависит от works
    op.create_table('work_prices',
                    sa.Column('work_price_id', sa.UUID(), nullable=False),
                    sa.Column('work_id', sa.UUID(), nullable=True),
                    sa.Column('name', sa.VARCHAR(), nullable=False),
                    sa.Column('category', sa.INTEGER(), nullable=False),
                    sa.Column('price', sa.NUMERIC(
                        precision=10, scale=2), nullable=False),
                    sa.Column('deleted', sa.BOOLEAN(), nullable=False),
                    sa.ForeignKeyConstraint(
                        ['work_id'], ['works.work_id'], name='work_prices_work_id_fkey'),
                    sa.PrimaryKeyConstraint(
                        'work_price_id', name='work_prices_pkey')
                    )


def downgrade() -> None:
    op.drop_table('work_prices')
    op.drop_table('project_schedules')
    op.drop_table('project_works')
    op.drop_table('shift_report_details')
    op.drop_table('shift_reports')
    op.drop_table('projects')
    op.drop_table('objects')
    op.drop_table('works')
    op.drop_table('work_categories')
    op.drop_table('object_statuses')
    op.drop_table('users')
    op.drop_table('roles')
