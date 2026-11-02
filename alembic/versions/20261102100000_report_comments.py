"""Add paginated shift and acceptance comment streams."""
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261102100000"
down_revision: Union[str, None] = "20261021130000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = (
    ("shift-comments-create", "POST /shift_reports/{shift_report_id}/comments"),
    ("shift-comments-list", "GET /shift_reports/{shift_report_id}/comments"),
    ("shift-comments-edit", "PATCH /shift_reports/comments/{comment_id}"),
    ("shift-comments-delete", "DELETE /shift_reports/comments/{comment_id}"),
    ("acceptance-comments-create", "POST /acceptances/{acceptance_id}/comments"),
    ("acceptance-comments-list", "GET /acceptances/{acceptance_id}/comments"),
    ("acceptance-comments-edit", "PATCH /acceptances/comments/{comment_id}"),
    ("acceptance-comments-delete", "DELETE /acceptances/comments/{comment_id}"),
    ("shift-comments-attachments-upload", "POST /shift_reports/comments/{comment_id}/attachments"),
    ("shift-comments-attachments-download", "GET /shift_reports/comments/{comment_id}/attachments/{attachment_id}/download"),
    ("acceptance-comments-attachments-upload", "POST /acceptances/comments/{comment_id}/attachments"),
    ("acceptance-comments-attachments-download", "GET /acceptances/comments/{comment_id}/attachments/{attachment_id}/download"),
)

def _comment_table(name: str, id_name: str, parent_name: str, parent_table: str, parent_pk: str):
    op.create_table(
        name,
        sa.Column(id_name, postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(parent_name, postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{parent_table}.{parent_pk}", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("created_at", sa.BigInteger(), server_default=sa.text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=True),
        sa.Column("browser_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(f"ix_{name}_{parent_name}_created_at", name, [parent_name, "created_at", id_name])

def _attachment_table(name: str, id_name: str, comment_fk: str, comment_table: str):
    op.create_table(
        name,
        sa.Column(id_name, postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(comment_fk, postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{comment_table}.{comment_fk}", ondelete="CASCADE"), nullable=False),
        sa.Column("attachment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attachments.attachment_id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint(comment_fk, "attachment_id", name=f"uq_{name}"),
    )

def upgrade() -> None:
    _comment_table("shift_report_comments", "shift_report_comment_id", "shift_report_id", "shift_reports", "shift_report_id")
    _comment_table("acceptance_comments", "acceptance_comment_id", "acceptance_id", "acceptances", "id")
    _attachment_table("shift_report_comment_attachments", "shift_report_comment_attachment_id", "shift_report_comment_id", "shift_report_comments")
    _attachment_table("acceptance_comment_attachments", "acceptance_comment_attachment_id", "acceptance_comment_id", "acceptance_comments")
    for code, description in PERMISSIONS:
        op.execute(sa.text("INSERT INTO permission_types (permission_type_id, code, description) VALUES (:id, :code, :description) ON CONFLICT (code) DO NOTHING").bindparams(id=uuid4(), code=code, description=description))

def downgrade() -> None:
    for code, _ in PERMISSIONS:
        op.execute(sa.text("DELETE FROM permission_types WHERE code = :code").bindparams(code=code))
    op.drop_table("acceptance_comment_attachments")
    op.drop_table("shift_report_comment_attachments")
    op.drop_index("ix_acceptance_comments_acceptance_id_created_at", table_name="acceptance_comments")
    op.drop_index("ix_shift_report_comments_shift_report_id_created_at", table_name="shift_report_comments")
    op.drop_table("acceptance_comments")
    op.drop_table("shift_report_comments")
