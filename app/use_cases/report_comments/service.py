from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID, uuid4

from app.adapters.report_comments.cleanup import (
    comment_attachment_cleanup,
    delete_s3_objects,
)
from app.database import db_globals
from app.database.models import (
    AcceptanceCommentAttachments,
    AcceptanceComments,
    Acceptances,
    Attachments,
    Projects,
    ShiftReportCommentAttachments,
    ShiftReportComments,
    ShiftReportDetails,
    ShiftReports,
    Users,
    WorkAcceptanceRelations,
)
from app.database.time_utils import utc_epoch_milliseconds
from app.use_cases.attachments import UploadFile


class CommentError(Exception):
    def __init__(self, message: str, status: int = 400):
        self.status = status
        super().__init__(message)


def is_comment_editable(created_at: int, now: int) -> bool:
    return 0 <= now - created_at <= 5 * 60 * 1000


@dataclass(frozen=True)
class CommentActor:
    user_id: UUID
    role: str


def ensure_comment_attachment_mutable(
    comment_author_id: UUID, created_at: int, actor: CommentActor, now: int
) -> None:
    if comment_author_id != actor.user_id:
        raise CommentError("Only the comment author can add attachments", 403)
    if not is_comment_editable(created_at, now):
        raise CommentError("Comment attachment window of five minutes has expired", 409)


class ReportCommentService:
    def _session(self):
        if db_globals.Session is None:
            raise RuntimeError("Database session is not initialized")
        return db_globals.Session()

    @staticmethod
    def _can_view_shift(session, report, actor: CommentActor) -> bool:
        if actor.role in {"admin", "manager"}:
            return True
        if actor.role == "project-leader":
            return session.get(Projects, report.project).project_leader == actor.user_id
        return actor.role == "user" and report.user == actor.user_id

    @staticmethod
    def _can_view_acceptance(session, acceptance, actor: CommentActor) -> bool:
        project = session.get(Projects, acceptance.project_id)
        if project is None:
            return False
        if actor.role in {"admin", "manager"}:
            return True
        if actor.role == "project-leader":
            return project.project_leader == actor.user_id
        if actor.role == "user":
            return (
                session.query(ShiftReports.shift_report_id)
                .join(
                    ShiftReportDetails,
                    ShiftReportDetails.shift_report == ShiftReports.shift_report_id,
                )
                .join(
                    WorkAcceptanceRelations,
                    WorkAcceptanceRelations.work_id == ShiftReportDetails.work,
                )
                .filter(
                    WorkAcceptanceRelations.acceptance_id == acceptance.id,
                    ShiftReports.user == actor.user_id,
                    ShiftReports.project == project.project_id,
                )
                .first()
                is not None
            )
        return False

    def _parent(self, session, kind: str, parent_id: UUID):
        if kind == "shift":
            return session.get(ShiftReports, parent_id)
        return session.get(Acceptances, parent_id)

    def _allowed(
        self, session, kind: str, parent, actor: CommentActor, *, create=False
    ) -> bool:
        if kind == "shift":
            if not self._can_view_shift(session, parent, actor):
                return False
            if not create:
                return True
            if actor.role in {"admin", "manager"}:
                return True
            if actor.role == "project-leader":
                project = session.get(Projects, parent.project)
                return project is not None and project.project_leader == actor.user_id
            return actor.role == "user" and parent.user == actor.user_id
        if not self._can_view_acceptance(session, parent, actor):
            return False
        return (
            actor.role in {"admin", "manager", "project-leader", "user"}
            if create
            else True
        )

    def list(
        self, kind: str, parent_id: UUID, actor: CommentActor, offset: int, limit: int
    ):
        session = self._session()
        try:
            parent = self._parent(session, kind, parent_id)
            if parent is None:
                raise CommentError("Entity not found", 404)
            if not self._allowed(session, kind, parent, actor):
                raise CommentError("Forbidden", 403)
            model, fk = (
                (ShiftReportComments, "shift_report_id")
                if kind == "shift"
                else (AcceptanceComments, "acceptance_id")
            )
            query = session.query(model).filter(getattr(model, fk) == parent_id)
            total = query.count()
            items = (
                query.order_by(
                    model.created_at.asc(),
                    model.shift_report_comment_id.asc()
                    if kind == "shift"
                    else model.acceptance_comment_id.asc(),
                )
                .offset(offset)
                .limit(limit)
                .all()
            )
            return total, [self._serialize(session, kind, item) for item in items]
        finally:
            session.close()

    def create(
        self,
        kind: str,
        parent_id: UUID,
        actor: CommentActor,
        text_value: str,
        browser_id: UUID | None,
    ):
        if not text_value.strip():
            raise CommentError("Comment text must not be empty")
        session = self._session()
        try:
            parent = self._parent(session, kind, parent_id)
            if parent is None:
                raise CommentError("Entity not found", 404)
            if not self._allowed(session, kind, parent, actor, create=True):
                raise CommentError("Forbidden", 403)
            model, fk = (
                (ShiftReportComments, "shift_report_id")
                if kind == "shift"
                else (AcceptanceComments, "acceptance_id")
            )
            item = model(
                **{
                    fk: parent_id,
                    "text": text_value.strip(),
                    "created_by": actor.user_id,
                    "created_at": utc_epoch_milliseconds(),
                    "browser_id": browser_id,
                }
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return self._serialize(session, kind, item)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def edit(self, kind: str, comment_id: UUID, actor: CommentActor, text_value: str):
        if not text_value.strip():
            raise CommentError("Comment text must not be empty")
        session = self._session()
        try:
            model = ShiftReportComments if kind == "shift" else AcceptanceComments
            item = session.get(model, comment_id)
            if item is None:
                raise CommentError("Comment not found", 404)
            if item.created_by != actor.user_id:
                raise CommentError("Only the author can edit a comment", 403)
            if not is_comment_editable(item.created_at, utc_epoch_milliseconds()):
                raise CommentError(
                    "Comment edit window of five minutes has expired", 409
                )
            parent = self._parent(
                session,
                kind,
                item.shift_report_id if kind == "shift" else item.acceptance_id,
            )
            if parent is None or not self._allowed(session, kind, parent, actor):
                raise CommentError("Forbidden", 403)
            item.text = text_value.strip()
            item.updated_at = utc_epoch_milliseconds()
            session.commit()
            session.refresh(item)
            return self._serialize(session, kind, item)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete(self, kind: str, comment_id: UUID, actor: CommentActor):
        if actor.role != "admin":
            raise CommentError("Only admin can delete comments", 403)
        session = self._session()
        try:
            model = ShiftReportComments if kind == "shift" else AcceptanceComments
            item = session.get(model, comment_id)
            if item is None:
                raise CommentError("Comment not found", 404)
            cleanup = comment_attachment_cleanup(session, kind, comment_id=comment_id)
            relation_model = (
                ShiftReportCommentAttachments
                if kind == "shift"
                else AcceptanceCommentAttachments
            )
            comment_fk = (
                "shift_report_comment_id"
                if kind == "shift"
                else "acceptance_comment_id"
            )
            session.query(relation_model).filter(
                getattr(relation_model, comment_fk) == comment_id
            ).delete(synchronize_session=False)
            session.delete(item)
            for attachment_id in cleanup.attachment_ids:
                attachment = session.get(Attachments, attachment_id)
                if attachment is not None:
                    session.delete(attachment)
            session.commit()
            delete_s3_objects(cleanup.s3_keys)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def upload(
        self, kind: str, comment_id: UUID, actor: CommentActor, files: list[UploadFile]
    ):
        from app.adapters.attachments import S3AttachmentStorage

        session = self._session()
        uploaded = []
        try:
            model = ShiftReportComments if kind == "shift" else AcceptanceComments
            item = session.get(model, comment_id)
            if item is None:
                raise CommentError("Comment not found", 404)
            ensure_comment_attachment_mutable(
                item.created_by,
                item.created_at,
                actor,
                utc_epoch_milliseconds(),
            )
            parent_id = item.shift_report_id if kind == "shift" else item.acceptance_id
            parent = self._parent(session, kind, parent_id)
            if parent is None or not self._allowed(session, kind, parent, actor):
                raise CommentError("Forbidden", 403)
            storage = S3AttachmentStorage()
            link_model = (
                ShiftReportCommentAttachments
                if kind == "shift"
                else AcceptanceCommentAttachments
            )
            comment_fk = (
                "shift_report_comment_id"
                if kind == "shift"
                else "acceptance_comment_id"
            )
            for file in files:
                attachment_id = uuid4()
                stored = storage.upload(
                    file.content,
                    target_type=f"{kind}_comment",
                    target_id=comment_id,
                    attachment_id=attachment_id,
                    filename=file.name,
                    content_type=file.content_type,
                )
                record = Attachments(
                    attachment_id=attachment_id,
                    name=stored.name,
                    s3_key=stored.key,
                    file_size=len(stored.content),
                    checksum=sha256(stored.content).hexdigest(),
                    meta={
                        "content_type": stored.content_type,
                        "extension": stored.name.rsplit(".", 1)[-1].lower(),
                    },
                    created_at=utc_epoch_milliseconds(),
                    created_by=actor.user_id,
                )
                session.add(record)
                session.add(
                    link_model(
                        **{comment_fk: comment_id, "attachment_id": attachment_id}
                    )
                )
                uploaded.append((storage, stored.key))
            session.commit()
            return self._serialize(session, kind, item)
        except Exception:
            session.rollback()
            for storage, key in uploaded:
                try:
                    storage.delete(key)
                except Exception:
                    pass
            raise
        finally:
            session.close()

    def download(
        self, kind: str, comment_id: UUID, attachment_id: UUID, actor: CommentActor
    ):
        from app.adapters.attachments import S3AttachmentStorage

        session = self._session()
        try:
            model = ShiftReportComments if kind == "shift" else AcceptanceComments
            item = session.get(model, comment_id)
            if item is None:
                raise CommentError("Comment not found", 404)
            parent_id = item.shift_report_id if kind == "shift" else item.acceptance_id
            parent = self._parent(session, kind, parent_id)
            if parent is None or not self._allowed(session, kind, parent, actor):
                raise CommentError("Forbidden", 403)
            link_model = (
                ShiftReportCommentAttachments
                if kind == "shift"
                else AcceptanceCommentAttachments
            )
            comment_fk = (
                "shift_report_comment_id"
                if kind == "shift"
                else "acceptance_comment_id"
            )
            link = (
                session.query(link_model)
                .filter(
                    getattr(link_model, comment_fk) == comment_id,
                    link_model.attachment_id == attachment_id,
                )
                .first()
            )
            attachment = session.get(Attachments, attachment_id) if link else None
            if attachment is None:
                raise CommentError("Attachment not found", 404)
            return (
                S3AttachmentStorage().download_bytes(attachment.s3_key),
                attachment.name,
                attachment.meta.get("content_type", "application/octet-stream"),
            )
        finally:
            session.close()

    @staticmethod
    def _serialize(session, kind, item):
        author = session.get(Users, item.created_by)
        id_field = (
            "shift_report_comment_id" if kind == "shift" else "acceptance_comment_id"
        )
        link_model = (
            ShiftReportCommentAttachments
            if kind == "shift"
            else AcceptanceCommentAttachments
        )
        comment_fk = (
            "shift_report_comment_id" if kind == "shift" else "acceptance_comment_id"
        )
        files = (
            session.query(Attachments)
            .join(link_model, link_model.attachment_id == Attachments.attachment_id)
            .filter(getattr(link_model, comment_fk) == getattr(item, id_field))
            .order_by(Attachments.created_at, Attachments.attachment_id)
            .all()
        )
        return {
            id_field: str(getattr(item, id_field)),
            "text": item.text,
            "created_by": str(item.created_by),
            "author_name": author.name if author else None,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "browser_id": str(item.browser_id) if item.browser_id else None,
            "attachments": [
                {
                    "attachment_id": str(file.attachment_id),
                    "name": file.name,
                    "file_size": file.file_size,
                    "checksum": file.checksum,
                    "meta": file.meta,
                    "created_at": file.created_at,
                    "created_by": str(file.created_by),
                }
                for file in files
            ],
        }
