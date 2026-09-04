import logging
from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID, uuid4

from app.domain.attachments import (
    Attachment,
    AttachmentConflictError,
    AttachmentForbiddenError,
    AttachmentNotFoundError,
    AttachmentTarget,
)
from app.use_cases.time_utils import utc_epoch_milliseconds

from .dto import AttachmentActor, UploadFile
from .ports import AttachmentRepository, AttachmentStorage

logger = logging.getLogger("ok_service")


def _ensure_view_access(target: AttachmentTarget, actor: AttachmentActor) -> None:
    if target.deleted:
        raise AttachmentConflictError("Deleted entity cannot be changed")
    if target.target_type == "project":
        if actor.role == "project-leader" and target.project_leader_id == actor.user_id:
            return
        if actor.role in {"admin", "manager"}:
            return
        raise AttachmentForbiddenError("Forbidden")
    if target.target_type == "object":
        if actor.role in {"admin", "manager", "project-leader", "user"}:
            return
        raise AttachmentForbiddenError("Forbidden")
    if target.target_type == "place":
        if actor.role in {"admin", "manager", "project-leader", "user"}:
            return
        raise AttachmentForbiddenError("Forbidden")
    if target.target_type == "acceptance":
        if actor.role in {"admin", "manager", "project-leader", "user"}:
            return
        raise AttachmentForbiddenError("Forbidden")
    if target.target_type == "shift_report":
        if actor.role == "user":
            if target.owner_id != actor.user_id:
                raise AttachmentForbiddenError("User cannot view not his shift report")
            return
        if actor.role in {"admin", "manager", "project-leader"}:
            return
        raise AttachmentForbiddenError("Forbidden")
    raise AttachmentNotFoundError("Attachment target not found")


def _ensure_mutation_access(
    target: AttachmentTarget, actor: AttachmentActor, *, delete: bool
) -> None:
    if target.deleted:
        raise AttachmentConflictError("Deleted entity cannot be changed")
    if target.target_type == "acceptance":
        if actor.role in {"admin", "manager"}:
            return
        raise AttachmentForbiddenError("Forbidden")
    if target.target_type in {"object", "place"}:
        if actor.role == "admin":
            return
        raise AttachmentForbiddenError("Forbidden")
    if target.target_type != "shift_report":
        _ensure_view_access(target, actor)
        return
    _ensure_view_access(target, actor)
    if target.leave_id is not None:
        raise AttachmentConflictError("Shift report linked to leave cannot be changed")
    if actor.role == "admin":
        return
    if actor.role == "manager":
        return
    if actor.role == "project-leader" and target.project_leader_id == actor.user_id:
        return
    if actor.role == "user" and not target.signed and target.owner_id == actor.user_id:
        return
    raise AttachmentForbiddenError("Forbidden")


@dataclass(slots=True)
class AttachmentUseCase:
    repository: AttachmentRepository
    storage: AttachmentStorage

    def upload(
        self,
        target_type: str,
        target_id: UUID,
        files: list[UploadFile],
        actor: AttachmentActor,
    ) -> list[Attachment]:
        if not files:
            raise ValueError("At least one file is required")
        target = self.repository.get_target(target_type, target_id)
        if target is None:
            raise AttachmentNotFoundError("Attachment target not found")
        _ensure_mutation_access(target, actor, delete=False)

        uploaded: list[Attachment] = []
        try:
            for file in files:
                attachment_id = uuid4()
                stored_file = self.storage.upload(
                    file.content,
                    target_type=target_type,
                    target_id=target_id,
                    attachment_id=attachment_id,
                    filename=file.name,
                    content_type=file.content_type,
                )
                uploaded.append(
                    Attachment(
                        attachment_id=attachment_id,
                        name=stored_file.name,
                        s3_key=stored_file.key,
                        file_size=len(stored_file.content),
                        checksum=sha256(stored_file.content).hexdigest(),
                        meta={
                            "content_type": stored_file.content_type,
                            "extension": stored_file.name.rsplit(".", 1)[-1].lower(),
                        },
                        created_at=utc_epoch_milliseconds(),
                        created_by=actor.user_id,
                    )
                )
            self.repository.create_attachments(target_type, target_id, uploaded)
        except Exception:
            for attachment in uploaded:
                try:
                    self.storage.delete(attachment.s3_key)
                except Exception as cleanup_error:
                    logger.error(
                        "Failed to compensate S3 attachment upload for key %s: %s",
                        attachment.s3_key,
                        cleanup_error,
                    )
            raise
        return uploaded

    def list(
        self, target_type: str, target_id: UUID, actor: AttachmentActor
    ) -> list[Attachment]:
        target = self.repository.get_target(target_type, target_id)
        if target is None:
            raise AttachmentNotFoundError("Attachment target not found")
        _ensure_view_access(target, actor)
        return self.repository.list_attachments(target_type, target_id)

    def download_bytes(
        self,
        target_type: str,
        target_id: UUID,
        attachment_id: UUID,
        actor: AttachmentActor,
    ) -> tuple[bytes, str, str]:
        target = self.repository.get_target(target_type, target_id)
        if target is None:
            raise AttachmentNotFoundError("Attachment target not found")
        _ensure_view_access(target, actor)
        attachment = self.repository.get_attachment(
            target_type, target_id, attachment_id
        )
        if attachment is None:
            raise AttachmentNotFoundError("Attachment not found")
        content_type = str(
            attachment.meta.get("content_type", "application/octet-stream")
        )
        return (
            self.storage.download_bytes(attachment.s3_key),
            attachment.name,
            content_type,
        )

    def delete(
        self,
        target_type: str,
        target_id: UUID,
        attachment_id: UUID,
        actor: AttachmentActor,
    ) -> None:
        target = self.repository.get_target(target_type, target_id)
        if target is None:
            raise AttachmentNotFoundError("Attachment target not found")
        _ensure_mutation_access(target, actor, delete=True)
        attachment = self.repository.get_attachment(
            target_type, target_id, attachment_id
        )
        if attachment is None:
            raise AttachmentNotFoundError("Attachment not found")
        deleted = self.repository.delete_attachment(
            target_type, target_id, attachment_id
        )
        if deleted is None:
            raise AttachmentNotFoundError("Attachment not found")
        try:
            self.storage.delete(attachment.s3_key)
        except Exception as cleanup_error:
            logger.error(
                "Attachment %s deleted from DB but S3 cleanup failed for key %s: %s",
                attachment_id,
                attachment.s3_key,
                cleanup_error,
            )
