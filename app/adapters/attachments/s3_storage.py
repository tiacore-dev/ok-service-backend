import logging
from asyncio import run
from io import BytesIO
from uuid import UUID

from botocore.exceptions import BotoCoreError, ClientError
from PIL import Image, ImageOps, UnidentifiedImageError

from app.domain.attachments import AttachmentStorageError
from app.s3.s3_manager import AsyncS3Manager
from app.use_cases.attachments.dto import StoredFile

logger = logging.getLogger("ok_service")
IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png"})


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
    ) -> StoredFile:
        normalized_name, detected_content_type = self._manager.validate_attachment(
            content, filename=filename, content_type=content_type
        )
        if normalized_name.rsplit(".", 1)[-1].lower() in IMAGE_EXTENSIONS:
            try:
                with Image.open(BytesIO(content)) as image:
                    image.load()
                    oriented_image = ImageOps.exif_transpose(image)
                    if oriented_image is None:
                        raise ValueError(
                            "Не удалось определить ориентацию изображения"
                        )
                    mode = (
                        "RGBA"
                        if oriented_image.mode in {"RGBA", "LA"}
                        or "transparency" in oriented_image.info
                        else "RGB"
                    )
                    converted = oriented_image.convert(mode)
                    output = BytesIO()
                    converted.save(output, format="WEBP", quality=80)
                    content = output.getvalue()
            except (UnidentifiedImageError, OSError) as error:
                raise ValueError(
                    "Не удалось преобразовать изображение в webp"
                ) from error
            normalized_name = f"{normalized_name.rsplit('.', 1)[0]}.webp"
            detected_content_type = "image/webp"
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
        return StoredFile(key, normalized_name, content, detected_content_type)

    def delete(self, key: str) -> None:
        try:
            run(self._manager.delete_file(key))
        except (BotoCoreError, ClientError, OSError, RuntimeError) as error:
            raise AttachmentStorageError("Unable to delete attachment") from error

    def download_bytes(self, key: str) -> bytes:
        try:
            return run(self._manager.download_bytes(key))
        except (BotoCoreError, ClientError, OSError, RuntimeError) as error:
            raise AttachmentStorageError("Unable to download attachment") from error
