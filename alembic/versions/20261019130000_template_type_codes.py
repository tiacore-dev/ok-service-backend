"""Английские значения enum типов шаблонов без изменения записей.

Revision ID: 20261019130000
Revises: 20261019120000
"""

from alembic import op

revision = "20261019130000"
down_revision = "20261019120000"
branch_labels = None
depends_on = None

TYPE_CODES = (
    ("Виды работ", "work_types"),
    ("Отчет по смене", "shift_report"),
    ("Отчет по смене - список", "shift_report_list"),
    ("Зарплатная ведомость", "payroll"),
    ("Отчет по объектам", "object_report"),
)


def upgrade() -> None:
    for label, code in TYPE_CODES:
        op.execute(f"ALTER TYPE template_types RENAME VALUE '{label}' TO '{code}'")


def downgrade() -> None:
    for label, code in reversed(TYPE_CODES):
        op.execute(f"ALTER TYPE template_types RENAME VALUE '{code}' TO '{label}'")
