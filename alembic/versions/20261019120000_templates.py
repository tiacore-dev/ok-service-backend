"""Хранилище шаблонов документов.

Revision ID: 20261019120000
Revises: 20261016120000
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261019120000"
down_revision = "20261016120000"
branch_labels = None
depends_on = None

TEMPLATE_TYPES = (
    "Виды работ",
    "Отчет по смене",
    "Отчет по смене - список",
    "Зарплатная ведомость",
    "Отчет по объектам",
)


def upgrade() -> None:
    enum = postgresql.ENUM(*TEMPLATE_TYPES, name="template_types", create_type=False)
    enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "templates",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template_type", enum, nullable=False),
        sa.Column("s3_key", sa.String(512), nullable=False, unique=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(255), nullable=False),
        sa.Column("output_file_name", sa.Text(), nullable=True),
        sa.Column(
            "is_horizontal", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column("is_pdf", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "is_default", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )
    op.create_index("ix_templates_template_type", "templates", ["template_type"])
    op.create_index(
        "uq_templates_default_type",
        "templates",
        ["template_type"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )


def downgrade() -> None:
    op.drop_table("templates")
    postgresql.ENUM(name="template_types").drop(op.get_bind(), checkfirst=True)
