from typing import Protocol
from uuid import UUID

from app.domain.attachments import Attachment, AttachmentTarget


class AttachmentRepository(Protocol):
    def get_target(self, target_type: str, target_id: UUID) -> AttachmentTarget | None: ...

    def create_attachments(
        self,
        target_type: str,
        target_id: UUID,
        attachments: list[Attachment],
    ) -> None: ...

    def list_attachments(self, target_type: str, target_id: UUID) -> list[Attachment]: ...

    def get_attachment(
        self, target_type: str, target_id: UUID, attachment_id: UUID
    ) -> Attachment | None: ...

    def delete_attachment(
        self, target_type: str, target_id: UUID, attachment_id: UUID
    ) -> Attachment | None: ...


class AttachmentStorage(Protocol):
    def upload(
        self,
        content: bytes,
        *,
        target_type: str,
        target_id: UUID,
        attachment_id: UUID,
        filename: str,
        content_type: str | None,
    ) -> tuple[str, str, str]: ...

    def delete(self, key: str) -> None: ...

    def download_bytes(self, key: str) -> bytes: ...
