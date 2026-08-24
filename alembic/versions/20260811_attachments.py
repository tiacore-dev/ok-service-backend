"""Add attachments and target relation tables.

Revision ID: 20260811_attachments
Revises: 20260811_place_rel_perms
Create Date: 2026-08-11
"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260811_attachments"
down_revision: Union[str, None] = "20260811_place_rel_perms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = tuple(
    (
        f"{target}-attachments-{action}",
        f"{method} /{target}/{target_id}/attachments{suffix}",
    )
    for target, target_id in (
        ("projects", "{project_id}"),
        ("shift_reports", "{shift_report_id}"),
        ("objects", "{object_id}"),
    )
    for action, method, suffix in (
        ("upload", "POST", ""),
        ("list", "GET", ""),
        ("download", "GET", "/{attachment_id}/download"),
        ("delete", "DELETE", "/{attachment_id}"),
    )
)


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("attachment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("s3_key", sa.String(length=512), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("attachment_id"),
        sa.UniqueConstraint("s3_key", name="uq_attachments_s3_key"),
    )
    for table_name, relation_id, target_column, target_table, target_key in (
        (
            "project_attachments",
            "project_attachment_id",
            "project_id",
            "projects",
            "project_id",
        ),
        (
            "shift_report_attachments",
            "shift_report_attachment_id",
            "shift_report_id",
            "shift_reports",
            "shift_report_id",
        ),
        (
            "object_attachments",
            "object_attachment_id",
            "object_id",
            "objects",
            "object_id",
        ),
    ):
        op.create_table(
            table_name,
            sa.Column(relation_id, postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(target_column, postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("attachment_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.ForeignKeyConstraint([target_column], [f"{target_table}.{target_key}"]),
            sa.ForeignKeyConstraint(
                ["attachment_id"], ["attachments.attachment_id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint(relation_id),
            sa.UniqueConstraint(target_column, "attachment_id", name=f"uq_{table_name}"),
        )

    bind = op.get_bind()
    for code, description in PERMISSIONS:
        bind.execute(
            sa.text(
                "INSERT INTO permission_types (permission_type_id, code, description) "
                "VALUES (:id, :code, :description) ON CONFLICT (code) DO NOTHING"
            ).bindparams(id=uuid4(), code=code, description=description)
        )
        permission_id = bind.execute(
            sa.text(
                "SELECT permission_type_id FROM permission_types WHERE code = :code"
            ).bindparams(code=code)
        ).scalar_one()
        existing = {
            row.api_key_id
            for row in bind.execute(
                sa.text(
                    "SELECT api_key_id FROM key_permission_type_relations "
                    "WHERE permission_type_id = :permission_id"
                ).bindparams(permission_id=permission_id)
            ).all()
        }
        keys = bind.execute(sa.text("SELECT api_key_id FROM api_keys")).all()
        relation_table = sa.table(
            "key_permission_type_relations",
            sa.column("id", sa.UUID()),
            sa.column("api_key_id", sa.UUID()),
            sa.column("permission_type_id", sa.UUID()),
        )
        rows = [
            {
                "id": uuid4(),
                "api_key_id": row.api_key_id,
                "permission_type_id": permission_id,
            }
            for row in keys
            if row.api_key_id not in existing
        ]
        if rows:
            bind.execute(sa.insert(relation_table), rows)


def downgrade() -> None:
    bind = op.get_bind()
    for code, _ in PERMISSIONS:
        bind.execute(
            sa.text(
                "DELETE FROM key_permission_type_relations WHERE permission_type_id = "
                "(SELECT permission_type_id FROM permission_types WHERE code = :code)"
            ).bindparams(code=code)
        )
        bind.execute(
            sa.text("DELETE FROM permission_types WHERE code = :code").bindparams(code=code)
        )
    op.drop_table("object_attachments")
    op.drop_table("shift_report_attachments")
    op.drop_table("project_attachments")
    op.drop_table("attachments")
