from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete

from app.adapters.attachments import S3AttachmentStorage
from app.database import db_globals
from app.database.models import (
    AcceptanceCommentAttachments,
    AcceptanceComments,
    Attachments,
    ShiftReportCommentAttachments,
    ShiftReportComments,
)

logger = logging.getLogger("ok_service")


@dataclass(frozen=True)
class CommentAttachmentCleanup:
    attachment_ids: tuple[UUID, ...]
    s3_keys: tuple[str, ...]


def comment_attachment_cleanup(
    session, kind: str, comment_id: UUID | None = None, parent_id: UUID | None = None
) -> CommentAttachmentCleanup:
    if kind == "shift":
        comment_model = ShiftReportComments
        relation_model = ShiftReportCommentAttachments
        comment_fk = "shift_report_comment_id"
        parent_fk = "shift_report_id"
    else:
        comment_model = AcceptanceComments
        relation_model = AcceptanceCommentAttachments
        comment_fk = "acceptance_comment_id"
        parent_fk = "acceptance_id"

    query = (
        session.query(Attachments.attachment_id, Attachments.s3_key)
        .join(relation_model, relation_model.attachment_id == Attachments.attachment_id)
        .join(
            comment_model,
            getattr(comment_model, comment_fk) == getattr(relation_model, comment_fk),
        )
    )
    if comment_id is not None:
        query = query.filter(getattr(comment_model, comment_fk) == comment_id)
    if parent_id is not None:
        query = query.filter(getattr(comment_model, parent_fk) == parent_id)
    records = query.all()
    return CommentAttachmentCleanup(
        attachment_ids=tuple(record.attachment_id for record in records),
        s3_keys=tuple(record.s3_key for record in records),
    )


def delete_attachment_metadata(attachment_ids: tuple[UUID, ...]) -> bool:
    if not attachment_ids:
        return True
    if db_globals.Session is None:
        logger.error(
            "Cannot clean comment attachments: database session is not initialized"
        )
        return False
    session = db_globals.Session()
    try:
        session.execute(
            delete(Attachments).where(Attachments.attachment_id.in_(attachment_ids))
        )
        session.commit()
        return True
    except Exception:
        session.rollback()
        logger.exception("Failed to delete comment attachment metadata")
        return False
    finally:
        session.close()


def delete_s3_objects(keys: tuple[str, ...]) -> None:
    if not keys:
        return
    storage = S3AttachmentStorage()
    for key in keys:
        try:
            storage.delete(key)
        except Exception:
            logger.exception("Failed to delete comment attachment from S3: %s", key)


def cleanup_after_parent_delete(cleanup: CommentAttachmentCleanup) -> None:
    if delete_attachment_metadata(cleanup.attachment_ids):
        delete_s3_objects(cleanup.s3_keys)
