"""Add attachment relation and API-key permissions for work acceptances."""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260903090000"
down_revision: Union[str, None] = "20260831130000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = (
    ("acceptances-attachments-upload", "POST /acceptances/{acceptance_id}/attachments"),
    ("acceptances-attachments-list", "GET /acceptances/{acceptance_id}/attachments"),
    ("acceptances-attachments-download", "GET /acceptances/{acceptance_id}/attachments/{attachment_id}/download"),
    ("acceptances-attachments-delete", "DELETE /acceptances/{acceptance_id}/attachments/{attachment_id}"),
)


def upgrade() -> None:
    op.create_table(
        "work_acceptance_attachments",
        sa.Column("work_acceptance_attachment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("acceptance_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attachment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["acceptance_id"], ["acceptances.id"]),
        sa.ForeignKeyConstraint(["attachment_id"], ["attachments.attachment_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("work_acceptance_attachment_id"),
        sa.UniqueConstraint("acceptance_id", "attachment_id", name="uq_work_acceptance_attachments"),
    )

    for code, description in PERMISSIONS:
        op.execute(sa.text(
            "INSERT INTO permission_types (permission_type_id, code, description) "
            "VALUES (:id, :code, :description) ON CONFLICT (code) DO NOTHING"
        ).bindparams(id=uuid4(), code=code, description=description))


def downgrade() -> None:
    for code, _ in PERMISSIONS:
        op.execute(sa.text(
            "DELETE FROM permission_types WHERE code = :code"
        ).bindparams(code=code))
    op.drop_table("work_acceptance_attachments")
