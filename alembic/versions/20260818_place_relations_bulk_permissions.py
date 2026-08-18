"""Add API-key permissions for bulk place relations."""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "20260818_place_rel_bulk"
down_revision: Union[str, None] = "20260818_place_attach"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = (
    ("project-place-relations-add-bulk", "POST /project_place_relations/add-bulk"),
    (
        "project-place-relations-delete-bulk",
        "DELETE /project_place_relations/delete-bulk",
    ),
    ("shift-place-relations-add-bulk", "POST /shift_place_relations/add-bulk"),
    ("shift-place-relations-delete-bulk", "DELETE /shift_place_relations/delete-bulk"),
)


def upgrade() -> None:
    bind = op.get_bind()
    permission_types = sa.table(
        "permission_types",
        sa.column("permission_type_id", sa.UUID()),
        sa.column("code", sa.String()),
    )
    relations = sa.table(
        "key_permission_type_relations",
        sa.column("id", sa.UUID()),
        sa.column("api_key_id", sa.UUID()),
        sa.column("permission_type_id", sa.UUID()),
    )
    for code, description in PERMISSIONS:
        bind.execute(
            sa.text(
                "INSERT INTO permission_types (permission_type_id, code, description) VALUES (:id, :code, :description) ON CONFLICT (code) DO NOTHING"
            ).bindparams(id=uuid4(), code=code, description=description)
        )
        permission_id = bind.execute(
            sa.select(permission_types.c.permission_type_id).where(
                permission_types.c.code == code
            )
        ).scalar_one()
        keys = bind.execute(sa.text("SELECT api_key_id FROM api_keys")).all()
        existing = {
            row.api_key_id
            for row in bind.execute(
                sa.text(
                    "SELECT api_key_id FROM key_permission_type_relations WHERE permission_type_id = :permission_id"
                ).bindparams(permission_id=permission_id)
            ).all()
        }
        bind.execute(
            sa.insert(relations),
            [
                {
                    "id": uuid4(),
                    "api_key_id": row.api_key_id,
                    "permission_type_id": permission_id,
                }
                for row in keys
                if row.api_key_id not in existing
            ],
        )


def downgrade() -> None:
    bind = op.get_bind()
    for code, _ in PERMISSIONS:
        bind.execute(
            sa.text(
                "DELETE FROM key_permission_type_relations WHERE permission_type_id = (SELECT permission_type_id FROM permission_types WHERE code = :code)"
            ).bindparams(code=code)
        )
        bind.execute(
            sa.text("DELETE FROM permission_types WHERE code = :code").bindparams(
                code=code
            )
        )
