"""Add attachment relation and API-key permissions for Places."""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260818_place_attach"
down_revision: Union[str, None] = "20260811_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = tuple(
    (
        f"places-attachments-{action}",
        f"{method} /places/{{place_id}}/attachments{suffix}",
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
        "place_attachments",
        sa.Column("place_attachment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("place_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attachment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["places.place_id"]),
        sa.ForeignKeyConstraint(
            ["attachment_id"], ["attachments.attachment_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("place_attachment_id"),
        sa.UniqueConstraint("place_id", "attachment_id", name="uq_place_attachments"),
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
            {"id": uuid4(), "api_key_id": row.api_key_id, "permission_type_id": permission_id}
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
    op.drop_table("place_attachments")
