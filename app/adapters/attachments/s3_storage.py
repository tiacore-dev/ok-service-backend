import logging
from asyncio import run
from uuid import UUID

from botocore.exceptions import BotoCoreError, ClientError

from app.domain.attachments import AttachmentStorageError
from app.s3.s3_manager import AsyncS3Manager

logger = logging.getLogger("ok_service")


class S3AttachmentStorage:
    def __init__(self, manager: AsyncS3Manager | None = None):
        self._manager = manager or AsyncS3Manager()

    def upload(
        self,
        content: bytes,
        *,
        target_type: str,
        target_id: UUID,
        attachment_id: UUID,
        filename: str,
        content_type: str | None,
    ) -> tuple[str, str, str]:
        normalized_name, detected_content_type = self._manager.validate_attachment(
            content, filename=filename, content_type=content_type
        )
        key = f"ok-service/{target_type}s/{target_id}/{attachment_id}_{normalized_name}"
        try:
            run(
                self._manager.upload_bytes(
                    content,
                    category=f"{target_type}s",
                    object_id=str(target_id),
                    filename=normalized_name,
                    content_type=detected_content_type,
                    key=key,
                )
            )
        except (BotoCoreError, ClientError, OSError, RuntimeError) as error:
            raise AttachmentStorageError("Unable to upload attachment") from error
        return key, normalized_name, detected_content_type

    def delete(self, key: str) -> None:
        try:
            run(self._manager.delete_file(key))
        except (BotoCoreError, ClientError, OSError, RuntimeError) as error:
            raise AttachmentStorageError("Unable to delete attachment") from error

    def download_url(self, key: str, *, filename: str) -> str:
        try:
            url = run(self._manager.generate_presigned_url(key, download_name=filename))
        except (BotoCoreError, ClientError, OSError, RuntimeError) as error:
            raise AttachmentStorageError("Unable to generate download URL") from error
        if url is None:
            raise RuntimeError("Unable to generate attachment download URL")
        return url
