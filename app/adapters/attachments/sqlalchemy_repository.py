from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy.orm import joinedload

from app.database import db_globals
from app.database.models import (
    Attachments,
    ObjectAttachments,
    Objects,
    ProjectAttachments,
    Projects,
    ShiftReportAttachments,
    ShiftReports,
)
from app.domain.attachments import Attachment, AttachmentTarget


class AttachmentRecord(TypedDict):
    attachment_id: UUID
    name: str
    s3_key: str
    file_size: int
    checksum: str
    meta: dict[str, str]
    created_at: int
    created_by: UUID


class SQLAlchemyAttachmentRepository:
    _relations = {
        "project": (ProjectAttachments, "project_id", Projects),
        "shift_report": (ShiftReportAttachments, "shift_report_id", ShiftReports),
        "object": (ObjectAttachments, "object_id", Objects),
    }

    @staticmethod
    def _session():
        if db_globals.Session is None:
            raise RuntimeError("Database session is not initialized")
        return db_globals.Session()

    @staticmethod
    def _attachment(model: Attachments) -> Attachment:
        record = cast(AttachmentRecord, model.__dict__)
        return Attachment(
            attachment_id=record["attachment_id"],
            name=record["name"],
            s3_key=record["s3_key"],
            file_size=record["file_size"],
            checksum=record["checksum"],
            meta=record["meta"],
            created_at=record["created_at"],
            created_by=record["created_by"],
        )

    def get_target(self, target_type: str, target_id: UUID) -> AttachmentTarget | None:
        session = self._session()
        try:
            if target_type == "project":
                project = session.get(Projects, target_id)
                if project is None:
                    return None
                return AttachmentTarget(
                    target_type=target_type,
                    target_id=target_id,
                    deleted=project.deleted,
                    project_leader_id=project.project_leader,
                )
            if target_type == "object":
                obj = session.get(Objects, target_id)
                if obj is None:
                    return None
                return AttachmentTarget(
                    target_type=target_type,
                    target_id=target_id,
                    deleted=obj.deleted,
                    owner_id=obj.manager,
                )
            if target_type == "shift_report":
                report = session.get(ShiftReports, target_id)
                if report is None:
                    return None
                return AttachmentTarget(
                    target_type=target_type,
                    target_id=target_id,
                    deleted=report.deleted,
                    owner_id=report.user,
                    signed=report.signed,
                    leave_id=report.leave_id,
                )
            return None
        finally:
            session.close()

    def create_attachments(
        self, target_type: str, target_id: UUID, attachments: list[Attachment]
    ) -> None:
        relation_model, target_column, _ = self._relations[target_type]
        session = self._session()
        try:
            for attachment in attachments:
                session.add(
                    Attachments(
                        attachment_id=attachment.attachment_id,
                        name=attachment.name,
                        s3_key=attachment.s3_key,
                        file_size=attachment.file_size,
                        checksum=attachment.checksum,
                        meta=attachment.meta,
                        created_at=attachment.created_at,
                        created_by=attachment.created_by,
                    )
                )
                session.add(
                    relation_model(
                        **{
                            target_column: target_id,
                            "attachment_id": attachment.attachment_id,
                        }
                    )
                )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _query_attachment(self, target_type: str, target_id: UUID, attachment_id: UUID):
        relation_model, target_column, _ = self._relations[target_type]
        session = self._session()
        relation = (
            session.query(relation_model)
            .options(joinedload(relation_model.attachment))
            .filter(
                getattr(relation_model, target_column) == target_id,
                relation_model.attachment_id == attachment_id,
            )
            .first()
        )
        return session, relation

    def list_attachments(self, target_type: str, target_id: UUID) -> list[Attachment]:
        relation_model, target_column, _ = self._relations[target_type]
        session = self._session()
        try:
            relations = (
                session.query(relation_model)
                .join(relation_model.attachment)
                .options(joinedload(relation_model.attachment))
                .filter(getattr(relation_model, target_column) == target_id)
                .order_by(Attachments.created_at.desc())
                .all()
            )
            return [self._attachment(relation.attachment) for relation in relations]
        finally:
            session.close()

    def get_attachment(
        self, target_type: str, target_id: UUID, attachment_id: UUID
    ) -> Attachment | None:
        session, relation = self._query_attachment(target_type, target_id, attachment_id)
        try:
            return self._attachment(relation.attachment) if relation is not None else None
        finally:
            session.close()

    def delete_attachment(
        self, target_type: str, target_id: UUID, attachment_id: UUID
    ) -> Attachment | None:
        session, relation = self._query_attachment(target_type, target_id, attachment_id)
        try:
            if relation is None:
                return None
            attachment = self._attachment(relation.attachment)
            session.delete(relation)
            session.flush()
            session.delete(relation.attachment)
            session.commit()
            return attachment
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
