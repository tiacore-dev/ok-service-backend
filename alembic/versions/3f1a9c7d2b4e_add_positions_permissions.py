"""Add positions permissions

Revision ID: 3f1a9c7d2b4e
Revises: 8ab65f512540
Create Date: 2026-07-08 00:00:00.000000

"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f1a9c7d2b4e"
down_revision: Union[str, None] = "8ab65f512540"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


POSITIONS_PERMISSIONS = [
    ("positions-create", "POST /positions/add"),
    ("positions-list", "GET /positions/all"),
    ("positions-view", "GET /positions/{position_id}/view"),
    ("positions-edit", "PATCH /positions/{position_id}/edit"),
    ("positions-delete-hard", "DELETE /positions/{position_id}/delete/hard"),
]


def upgrade() -> None:
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
            for code, description in POSITIONS_PERMISSIONS
        ],
    )


def downgrade() -> None:
    permission_types_table = sa.table(
        "permission_types",
        sa.column("code", sa.String()),
    )
    op.execute(
        permission_types_table.delete().where(
            permission_types_table.c.code.in_(
                [code for code, _description in POSITIONS_PERMISSIONS]
            )
        )
    )
