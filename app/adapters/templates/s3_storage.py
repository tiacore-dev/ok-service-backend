from asyncio import run
from uuid import UUID, uuid4

from botocore.exceptions import BotoCoreError, ClientError

from app.domain.templates import TemplateStorageError
from app.s3.s3_manager import AsyncS3Manager, FileValidationError


class S3TemplateStorage:
    def __init__(self, manager: AsyncS3Manager | None = None):
        self._manager = manager or AsyncS3Manager()

    def upload(
        self, template_id: UUID, content: bytes, filename: str, content_type: str | None
    ) -> tuple[str, str, str]:
        if filename.rsplit(".", 1)[-1].lower() not in {"docx", "xlsx"}:
            raise FileValidationError("Разрешены только файлы .docx и .xlsx")
        name, mime = self._manager.validate_attachment(
            content, filename=filename, content_type=content_type
        )
        if len(name) > 255:
            raise FileValidationError("Имя файла не должно превышать 255 символов")
        key = f"ok-service/templates/{template_id}/{uuid4()}_{name}"
        try:
            run(
                self._manager.upload_bytes(
                    content,
                    category="templates",
                    object_id=str(template_id),
                    filename=name,
                    content_type=mime,
                    key=key,
                )
            )
        except (BotoCoreError, ClientError, OSError, RuntimeError) as error:
            raise TemplateStorageError("Unable to upload template") from error
        return key, name, mime

    def delete(self, key: str) -> None:
        try:
            run(self._manager.delete_file(key))
        except (BotoCoreError, ClientError, OSError, RuntimeError) as error:
            raise TemplateStorageError("Unable to delete template") from error

    def download(self, key: str) -> bytes:
        try:
            return run(self._manager.download_bytes(key))
        except (BotoCoreError, ClientError, OSError, RuntimeError) as error:
            raise TemplateStorageError("Unable to download template") from error
