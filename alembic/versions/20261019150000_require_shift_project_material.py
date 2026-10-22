"""Обязательная строка спецификации вместо справочного материала расхода.

Revision ID: 20261019150000
Revises: 20261019140000
"""

import logging

import sqlalchemy as sa

from alembic import op

revision = "20261019150000"
down_revision = "20261019140000"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")


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
    # Keep independent snapshots, including across downgrade/upgrade cycles.
    op.execute("""
        CREATE TABLE IF NOT EXISTS shift_report_materials_unmatched_archive (
            archive_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            shift_report_material_id uuid NOT NULL,
            shift_report uuid NOT NULL,
            material uuid NOT NULL,
            project_material uuid,
            quantity numeric(10, 2) NOT NULL,
            shift_report_detail uuid,
            created_at bigint NOT NULL,
            created_by uuid NOT NULL,
            archived_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
            migration_revision text NOT NULL DEFAULT '20261019150000',
            restored_at timestamptz
        )
    """)
    archive_sql = sa.text("""
        WITH removed AS (
            DELETE FROM shift_report_materials WHERE project_material IS NULL
            RETURNING shift_report_material_id, shift_report, material,
                      project_material, quantity, shift_report_detail,
                      created_at, created_by
        ), archived AS (
            INSERT INTO shift_report_materials_unmatched_archive (
                shift_report_material_id, shift_report, material,
                project_material, quantity, shift_report_detail,
                created_at, created_by
            )
            SELECT shift_report_material_id, shift_report, material,
                   project_material, quantity, shift_report_detail,
                   created_at, created_by
            FROM removed
            RETURNING archive_id
        )
        SELECT count(*) FROM archived
    """)
    if op.get_context().as_sql:
        op.execute(archive_sql)
    else:
        count = op.get_bind().execute(archive_sql).scalar_one()
        logger.info("Archived and removed %s unmatched shift_report_materials", count)
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
    # The table may be absent on databases upgraded by the earlier cleanup version.
    op.execute("""
        DO $$
        BEGIN
            IF to_regclass('shift_report_materials_unmatched_archive') IS NOT NULL THEN
                WITH restored AS (
                    INSERT INTO shift_report_materials (
                        shift_report_material_id, shift_report, material,
                        project_material, quantity, shift_report_detail,
                        created_at, created_by
                    )
                    SELECT shift_report_material_id, shift_report, material,
                           project_material, quantity, shift_report_detail,
                           created_at, created_by
                    FROM shift_report_materials_unmatched_archive
                    WHERE migration_revision = '20261019150000'
                      AND restored_at IS NULL
                    RETURNING shift_report_material_id
                )
                UPDATE shift_report_materials_unmatched_archive
                SET restored_at = CURRENT_TIMESTAMP
                WHERE migration_revision = '20261019150000'
                  AND restored_at IS NULL
                  AND shift_report_material_id IN (
                      SELECT shift_report_material_id FROM restored
                  );
            END IF;
        END
        $$;
    """)
