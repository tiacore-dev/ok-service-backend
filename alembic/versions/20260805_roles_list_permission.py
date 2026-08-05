"""Add roles list permission and grant it to existing API keys.

Revision ID: 20260805_roles_list_permission
Revises: 20260805_shift_report_leave_id
"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_roles_list_permission"
down_revision: Union[str, None] = "20260805_shift_report_leave_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSION_CODE = "roles-list"
PERMISSION_DESCRIPTION = "GET /roles/all"


def upgrade() -> None:
    permission_types = sa.table(
        "permission_types",
        sa.column("permission_type_id", sa.UUID()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    permission_id = uuid4()
    op.execute(
        sa.text(
            """
            INSERT INTO permission_types (permission_type_id, code, description)
            VALUES (:permission_type_id, :code, :description)
            ON CONFLICT (code) DO NOTHING
            """
        ).bindparams(
            permission_type_id=permission_id,
            code=PERMISSION_CODE,
            description=PERMISSION_DESCRIPTION,
        )
    )

    actual_permission_id = op.get_bind().execute(
        sa.select(permission_types.c.permission_type_id).where(
            permission_types.c.code == PERMISSION_CODE
        )
    ).scalar_one()

    existing_relations = {
        row.api_key_id
        for row in op.get_bind()
        .execute(
            sa.text(
                """
                SELECT api_key_id
                FROM key_permission_type_relations
                WHERE permission_type_id = :permission_type_id
                """
            ).bindparams(permission_type_id=actual_permission_id)
        )
        .all()
    }
    api_key_ids = op.get_bind().execute(sa.text("SELECT api_key_id FROM api_keys")).all()
    op.bulk_insert(
        sa.table(
            "key_permission_type_relations",
            sa.column("id", sa.UUID()),
            sa.column("api_key_id", sa.UUID()),
            sa.column("permission_type_id", sa.UUID()),
        ),
        [
            {
                "id": uuid4(),
                "api_key_id": row.api_key_id,
                "permission_type_id": actual_permission_id,
            }
            for row in api_key_ids
            if row.api_key_id not in existing_relations
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM key_permission_type_relations
            WHERE permission_type_id = (
                SELECT permission_type_id
                FROM permission_types
                WHERE code = :code
            )
            """
        ).bindparams(code=PERMISSION_CODE)
    )
    op.execute(
        sa.text("DELETE FROM permission_types WHERE code = :code").bindparams(
            code=PERMISSION_CODE
        )
    )
