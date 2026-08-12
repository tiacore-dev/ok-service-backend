from uuid import UUID

from .sqlalchemy_repository import SQLAlchemyAttachmentRepository


def list_attachment_view_data(
    target_type: str,
    target_id: UUID,
    repository: SQLAlchemyAttachmentRepository | None = None,
    storage: object | None = None,
) -> list[dict[str, object]]:
    """Build attachment metadata for an already authorized view."""
    attachment_repository = repository or SQLAlchemyAttachmentRepository()
    return [
        {
            "attachment_id": str(attachment.attachment_id),
            "name": attachment.name,
            "file_size": attachment.file_size,
            "checksum": attachment.checksum,
            "meta": attachment.meta,
            "created_at": attachment.created_at,
            "created_by": str(attachment.created_by),
        }
        for attachment in attachment_repository.list_attachments(target_type, target_id)
    ]
