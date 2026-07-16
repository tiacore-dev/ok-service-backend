"""Add api keys and permission types

Revision ID: e1f4b8a9c2d1
Revises: 755c46649157
Create Date: 2026-05-20 14:55:00.000000

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f4b8a9c2d1"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS = [
    ("users-create", "POST /users/add"),
    ("users-list", "GET /users/all"),
    ("users-delete-hard", "DELETE /users/{user_id}/delete/hard"),
    ("users-delete-soft", "PATCH /users/{user_id}/delete/soft"),
    ("users-edit", "PATCH /users/{user_id}/edit"),
    ("users-restore", "PATCH /users/{user_id}/restore"),
    ("users-view", "GET /users/{user_id}/view"),
    ("cities-create", "POST /cities/add"),
    ("cities-list", "GET /cities/all"),
    ("cities-delete-hard", "DELETE /cities/{city_id}/delete/hard"),
    ("cities-delete-soft", "PATCH /cities/{city_id}/delete/soft"),
    ("cities-edit", "PATCH /cities/{city_id}/edit"),
    ("cities-view", "GET /cities/{city_id}/view"),
    ("leaves-create", "POST /leaves/add"),
    ("leaves-list", "GET /leaves/all"),
    ("leaves-reasons-list", "GET /leaves/reasons/all"),
    ("leaves-delete-hard", "DELETE /leaves/{leave_id}/delete/hard"),
    ("leaves-delete-soft", "PATCH /leaves/{leave_id}/delete/soft"),
    ("leaves-edit", "PATCH /leaves/{leave_id}/edit"),
    ("leaves-view", "GET /leaves/{leave_id}/view"),
    ("object-statuses-list", "GET /object_statuses/all"),
    ("work-categories-create", "POST /work_categories/add"),
    ("work-categories-list", "GET /work_categories/all"),
    (
        "work-categories-delete-hard",
        "DELETE /work_categories/{work_category_id}/delete/hard",
    ),
    (
        "work-categories-delete-soft",
        "PATCH /work_categories/{work_category_id}/delete/soft",
    ),
    ("work-categories-edit", "PATCH /work_categories/{work_category_id}/edit"),
    ("work-categories-view", "GET /work_categories/{work_category_id}/view"),
    ("objects-create", "POST /objects/add"),
    ("objects-list", "GET /objects/all"),
    ("objects-delete-hard", "DELETE /objects/{object_id}/delete/hard"),
    ("objects-delete-soft", "PATCH /objects/{object_id}/delete/soft"),
    ("objects-edit", "PATCH /objects/{object_id}/edit"),
    ("objects-view", "GET /objects/{object_id}/view"),
    ("projects-create", "POST /projects/add"),
    ("projects-list", "GET /projects/all"),
    ("projects-delete-hard", "DELETE /projects/{project_id}/delete/hard"),
    ("projects-delete-soft", "PATCH /projects/{project_id}/delete/soft"),
    ("projects-edit", "PATCH /projects/{project_id}/edit"),
    ("projects-get-stat", "GET /projects/{project_id}/get-stat"),
    (
        "projects-get-stat-by-project-materials",
        "GET /projects/{project_id}/get-stat-by-project-materials",
    ),
    ("projects-view", "GET /projects/{project_id}/view"),
    ("works-create", "POST /works/add"),
    ("works-list", "GET /works/all"),
    ("works-delete-hard", "DELETE /works/{work_id}/delete/hard"),
    ("works-delete-soft", "PATCH /works/{work_id}/delete/soft"),
    ("works-edit", "PATCH /works/{work_id}/edit"),
    ("works-view", "GET /works/{work_id}/view"),
    ("work-prices-create", "POST /work_prices/add"),
    ("work-prices-list", "GET /work_prices/all"),
    ("work-prices-delete-hard", "DELETE /work_prices/{work_price_id}/delete/hard"),
    ("work-prices-delete-soft", "PATCH /work_prices/{work_price_id}/delete/soft"),
    ("work-prices-edit", "PATCH /work_prices/{work_price_id}/edit"),
    ("work-prices-view", "GET /work_prices/{work_price_id}/view"),
    ("materials-create", "POST /materials/add"),
    ("materials-list", "GET /materials/all"),
    ("materials-delete-hard", "DELETE /materials/{material_id}/delete/hard"),
    ("materials-delete-soft", "PATCH /materials/{material_id}/delete/soft"),
    ("materials-edit", "PATCH /materials/{material_id}/edit"),
    ("materials-view", "GET /materials/{material_id}/view"),
    ("work-material-relations-create", "POST /work_material_relations/add"),
    ("work-material-relations-list", "GET /work_material_relations/all"),
    (
        "work-material-relations-delete-hard",
        "DELETE /work_material_relations/{relation_id}/delete/hard",
    ),
    (
        "work-material-relations-edit",
        "PATCH /work_material_relations/{relation_id}/edit",
    ),
    ("work-material-relations-view", "GET /work_material_relations/{relation_id}/view"),
    ("project-materials-create", "POST /project_materials/add"),
    ("project-materials-list", "GET /project_materials/all"),
    (
        "project-materials-delete-hard",
        "DELETE /project_materials/{project_material_id}/delete/hard",
    ),
    ("project-materials-edit", "PATCH /project_materials/{project_material_id}/edit"),
    ("project-materials-view", "GET /project_materials/{project_material_id}/view"),
    ("shift-report-materials-create", "POST /shift_report_materials/add"),
    ("shift-report-materials-list", "GET /shift_report_materials/all"),
    (
        "shift-report-materials-delete-hard",
        "DELETE /shift_report_materials/{shift_report_material_id}/delete/hard",
    ),
    (
        "shift-report-materials-edit",
        "PATCH /shift_report_materials/{shift_report_material_id}/edit",
    ),
    (
        "shift-report-materials-view",
        "GET /shift_report_materials/{shift_report_material_id}/view",
    ),
    ("project-works-create", "POST /project_works/add"),
    ("project-works-create-many", "POST /project_works/add/many"),
    ("project-works-list", "GET /project_works/all"),
    (
        "project-works-delete-hard",
        "DELETE /project_works/{project_work_id}/delete/hard",
    ),
    ("project-works-delete-soft", "PATCH /project_works/{project_work_id}/delete/soft"),
    ("project-works-edit", "PATCH /project_works/{project_work_id}/edit"),
    ("project-works-view", "GET /project_works/{project_work_id}/view"),
    ("project-schedules-create", "POST /project_schedules/add"),
    ("project-schedules-list", "GET /project_schedules/all"),
    (
        "project-schedules-delete-hard",
        "DELETE /project_schedules/{schedule_id}/delete/hard",
    ),
    ("project-schedules-edit", "PATCH /project_schedules/{schedule_id}/edit"),
    ("project-schedules-view", "GET /project_schedules/{schedule_id}/view"),
    ("shift-reports-create", "POST /shift_reports/add"),
    ("shift-reports-list", "GET /shift_reports/all"),
    ("shift-reports-delete-hard", "DELETE /shift_reports/{report_id}/delete/hard"),
    ("shift-reports-delete-soft", "PATCH /shift_reports/{report_id}/delete/soft"),
    ("shift-reports-edit", "PATCH /shift_reports/{report_id}/edit"),
    ("shift-reports-view", "GET /shift_reports/{report_id}/view"),
    ("shift-report-details-create", "POST /shift_report_details/add"),
    ("shift-report-details-create-many", "POST /shift_report_details/add/many"),
    ("shift-report-details-list", "GET /shift_report_details/all"),
    (
        "shift-report-details-all-by-reports",
        "POST /shift_report_details/all-by-reports",
    ),
    (
        "shift-report-details-delete-hard",
        "DELETE /shift_report_details/{detail_id}/delete/hard",
    ),
    ("shift-report-details-edit", "PATCH /shift_report_details/{detail_id}/edit"),
    ("shift-report-details-view", "GET /shift_report_details/{detail_id}/view"),
]


def upgrade() -> None:
    op.create_table(
        "permission_types",
        sa.Column("permission_type_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("permission_type_id"),
        sa.UniqueConstraint("code", name="uq_permission_types_code"),
    )

    op.create_table(
        "api_keys",
        sa.Column("api_key_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.BigInteger(),
            server_default=sa.text("EXTRACT(EPOCH FROM NOW())"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("api_key_id"),
        sa.UniqueConstraint("name", name="uq_api_keys_name"),
        sa.UniqueConstraint("token", name="uq_api_keys_token"),
    )

    op.create_table(
        "key_permission_type_relations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("api_key_id", sa.UUID(), nullable=False),
        sa.Column("permission_type_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["api_key_id"], ["api_keys.api_key_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["permission_type_id"],
            ["permission_types.permission_type_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "api_key_id",
            "permission_type_id",
            name="uq_key_permission_type_relations_api_key_permission",
        ),
    )

    permission_types_table = sa.table(
        "permission_types",
        sa.column("permission_type_id", sa.UUID()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )

    op.bulk_insert(
        permission_types_table,
        [
            {
                "permission_type_id": uuid.uuid4(),
                "code": code,
                "description": description,
            }
            for code, description in PERMISSIONS
        ],
    )


def downgrade() -> None:
    op.drop_table("key_permission_type_relations")
    op.drop_table("api_keys")
    op.drop_table("permission_types")
