"""Связь фактического расхода со строкой материала спецификации.

Revision ID: 20261019140000
Revises: 20261019130000
"""

import sqlalchemy as sa

from alembic import op

revision = "20261019140000"
down_revision = "20261019130000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_project_materials_shift_matching",
        "project_materials",
        ["project", "project_work", "material", "created_at", "project_material_id"],
    )
    op.add_column(
        "shift_report_materials",
        sa.Column("project_material", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_shift_report_materials_project_material",
        "shift_report_materials",
        "project_materials",
        ["project_material"],
        ["project_material_id"],
        ondelete="NO ACTION",
    )
    op.create_index(
        "ix_shift_report_materials_project_material",
        "shift_report_materials",
        ["project_material"],
    )
    op.execute(
        sa.text("""
        UPDATE shift_report_materials AS sm
        SET project_material = (
            SELECT pm.project_material_id
            FROM project_materials AS pm
            JOIN shift_reports AS sr ON sr.project = pm.project
            JOIN shift_report_details AS detail
              ON detail.shift_report = sr.shift_report_id
             AND detail.project_work = pm.project_work
            WHERE sr.shift_report_id = sm.shift_report
              AND detail.shift_report_detail_id = sm.shift_report_detail
              AND pm.material = sm.material
            ORDER BY pm.created_at ASC, pm.project_material_id ASC
            LIMIT 1
        )
    """)
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shift_report_materials_project_material",
        table_name="shift_report_materials",
    )
    op.drop_constraint(
        "fk_shift_report_materials_project_material",
        "shift_report_materials",
        type_="foreignkey",
    )
    op.drop_column("shift_report_materials", "project_material")
    op.drop_index("ix_project_materials_shift_matching", table_name="project_materials")
