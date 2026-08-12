from uuid import UUID

from .s3_storage import S3AttachmentStorage
from .sqlalchemy_repository import SQLAlchemyAttachmentRepository


def list_attachment_view_data(
    target_type: str,
    target_id: UUID,
    repository: SQLAlchemyAttachmentRepository | None = None,
    storage: S3AttachmentStorage | None = None,
) -> list[dict[str, object]]:
    """Build attachment metadata and preview URLs for an already authorized view."""
    attachment_repository = repository or SQLAlchemyAttachmentRepository()
    attachment_storage = storage or S3AttachmentStorage()
    return [
        {
            "attachment_id": str(attachment.attachment_id),
            "name": attachment.name,
            "file_size": attachment.file_size,
            "checksum": attachment.checksum,
            "meta": attachment.meta,
            "created_at": attachment.created_at,
            "created_by": str(attachment.created_by),
            "download_url": attachment_storage.download_url(
                attachment.s3_key, filename=attachment.name
            ),
        }
        for attachment in attachment_repository.list_attachments(target_type, target_id)
    ]
