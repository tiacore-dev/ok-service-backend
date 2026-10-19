"""Обязательная строка спецификации вместо справочного материала расхода.

Revision ID: 20261019150000
Revises: 20261019140000
"""

import sqlalchemy as sa

from alembic import op

revision = "20261019150000"
down_revision = "20261019140000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Retry unresolved rows if the nullable stage was applied separately.
    op.execute("""
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
        WHERE sm.project_material IS NULL
    """)
    op.execute("""
        DO $$
        DECLARE
            unmatched_count bigint;
            sample_ids text;
        BEGIN
            SELECT count(*) INTO unmatched_count
            FROM shift_report_materials
            WHERE project_material IS NULL;

            IF unmatched_count > 0 THEN
                SELECT string_agg(shift_report_material_id::text, ', '
                                 ORDER BY shift_report_material_id)
                INTO sample_ids
                FROM (
                    SELECT shift_report_material_id
                    FROM shift_report_materials
                    WHERE project_material IS NULL
                    ORDER BY shift_report_material_id
                    LIMIT 20
                ) AS unmatched;

                RAISE EXCEPTION
                    'Migration 20261019150000 blocked: % unmatched shift_report_materials. First 20 IDs: %',
                    unmatched_count, sample_ids
                    USING HINT = 'Reconcile these records before retrying alembic upgrade head. No usage records are deleted. See docs/shift-report-materials-rules.md for the full diagnostic query.';
            END IF;
        END
        $$;
    """)
    op.alter_column(
        "shift_report_materials",
        "project_material",
        existing_type=sa.UUID(),
        nullable=False,
    )
    op.drop_column("shift_report_materials", "material")


def downgrade() -> None:
    op.add_column(
        "shift_report_materials", sa.Column("material", sa.UUID(), nullable=True)
    )
    op.execute("""
        UPDATE shift_report_materials AS sm
        SET material = pm.material
        FROM project_materials AS pm
        WHERE pm.project_material_id = sm.project_material
    """)
    op.alter_column(
        "shift_report_materials", "material", existing_type=sa.UUID(), nullable=False
    )
    op.create_foreign_key(
        "shift_report_materials_material_fkey",
        "shift_report_materials",
        "materials",
        ["material"],
        ["material_id"],
        ondelete="CASCADE",
    )
    op.alter_column(
        "shift_report_materials",
        "project_material",
        existing_type=sa.UUID(),
        nullable=True,
    )
