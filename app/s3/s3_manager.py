import logging
import re
import zipfile
from io import BytesIO
from pathlib import PurePath
from urllib.parse import quote

import aioboto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

from config import Config as conf

load_dotenv()

logger = logging.getLogger("ok_service")

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024
OLE_COMPOUND_FILE_HEADER = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
EXECUTABLE_FILE_SIGNATURES = (
    b"MZ",
    b"\x7fELF",
    b"\xfe\xed\xfa\xce",
    b"\xfe\xed\xfa\xcf",
    b"\xce\xfa\xed\xfe",
    b"\xcf\xfa\xed\xfe",
)
EXECUTABLE_FILE_EXTENSIONS = frozenset(
    {"apk", "bat", "cmd", "com", "dll", "exe", "jar", "msi", "ps1", "scr", "sh"}
)

ALLOWED_FILE_TYPES: dict[str, tuple[str, frozenset[str]]] = {
    "pdf": ("application/pdf", frozenset({"application/pdf"})),
    "doc": ("application/msword", frozenset({"application/msword"})),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        frozenset(
            {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        ),
    ),
    "xls": ("application/vnd.ms-excel", frozenset({"application/vnd.ms-excel"})),
    "xlsx": (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        frozenset(
            {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
        ),
    ),
    "ppt": (
        "application/vnd.ms-powerpoint",
        frozenset({"application/vnd.ms-powerpoint"}),
    ),
    "pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        frozenset(
            {
                "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            }
        ),
    ),
    "txt": ("text/plain", frozenset({"text/plain"})),
    "csv": ("text/csv", frozenset({"text/csv", "application/csv"})),
    "jpg": ("image/jpeg", frozenset({"image/jpeg"})),
    "jpeg": ("image/jpeg", frozenset({"image/jpeg"})),
    "png": ("image/png", frozenset({"image/png"})),
    "gif": ("image/gif", frozenset({"image/gif"})),
    "webp": ("image/webp", frozenset({"image/webp"})),
    "mp3": ("audio/mpeg", frozenset({"audio/mpeg"})),
    "wav": ("audio/wav", frozenset({"audio/wav", "audio/x-wav"})),
    "ogg": ("audio/ogg", frozenset({"audio/ogg"})),
    "m4a": ("audio/mp4", frozenset({"audio/mp4", "audio/x-m4a"})),
    "mp4": ("video/mp4", frozenset({"video/mp4"})),
    "webm": ("video/webm", frozenset({"video/webm"})),
    "mov": ("video/quicktime", frozenset({"video/quicktime"})),
    "zip": (
        "application/zip",
        frozenset({"application/zip", "application/x-zip-compressed"}),
    ),
}


class FileValidationError(ValueError):
    """Файл не соответствует правилам загрузки вложений."""


def build_storage_key_path(
    category: str,
    object_id: str,
    filename: str,
) -> str:
    prefix = "ok-service"
    return f"{prefix}/{category}/{object_id}/{filename}"


class AsyncS3Manager:
    endpoint_url = conf.ENDPOINT_URL
    region_name = conf.REGION_NAME
    aws_access_key_id = conf.AWS_ACCESS_KEY_ID
    aws_secret_access_key = conf.AWS_SECRET_ACCESS_KEY
    bucket_name = conf.BUCKET_NAME

    _boto_config = Config(
        signature_version="s3v4",
        s3={"addressing_style": "path"},
        retries={"max_attempts": 3, "mode": "standard"},
    )

    def _get_session(self):
        return aioboto3.Session()

    def _normalize_filename(self, filename: str) -> str:
        filename = filename.strip()
        filename = filename.replace(" ", "_")
        filename = re.sub(r"[^\w.\-]", "", filename)
        return filename

    def _validate_filename(self, filename: str) -> tuple[str, str]:
        if (
            not filename
            or "/" in filename
            or "\\" in filename
            or filename != PurePath(filename).name
        ):
            raise FileValidationError(
                "Имя файла должно быть непустым и не содержать пути"
            )

        normalized_filename = self._normalize_filename(filename)
        stem, separator, extension = normalized_filename.rpartition(".")
        if not separator or not stem or not extension:
            raise FileValidationError("Файл должен иметь разрешённое расширение")

        extension = extension.lower()
        if extension not in ALLOWED_FILE_TYPES:
            raise FileValidationError(
                f"Файлы с расширением .{extension} не поддерживаются"
            )
        return normalized_filename, extension

    def _validate_content_type(self, extension: str, content_type: str | None) -> str:
        detected_content_type, allowed_content_types = ALLOWED_FILE_TYPES[extension]
        if content_type is None:
            return detected_content_type

        normalized_content_type = content_type.split(";", maxsplit=1)[0].strip().lower()
        if normalized_content_type not in allowed_content_types:
            raise FileValidationError(
                f"MIME-тип {normalized_content_type!r} не соответствует .{extension}"
            )
        return detected_content_type

    def _validate_zip_structure(self, file_bytes: bytes, extension: str) -> None:
        if not zipfile.is_zipfile(BytesIO(file_bytes)):
            raise FileValidationError(f"Содержимое файла не соответствует .{extension}")

        required_members = {
            "docx": {"[Content_Types].xml", "word/document.xml"},
            "xlsx": {"[Content_Types].xml", "xl/workbook.xml"},
            "pptx": {"[Content_Types].xml", "ppt/presentation.xml"},
        }
        with zipfile.ZipFile(BytesIO(file_bytes)) as archive:
            members = set(archive.namelist())
        if any(
            member.rsplit("/", maxsplit=1)[-1].rsplit(".", maxsplit=1)[-1].lower()
            in EXECUTABLE_FILE_EXTENSIONS
            for member in members
            if "." in member.rsplit("/", maxsplit=1)[-1]
        ):
            raise FileValidationError("ZIP-архив не должен содержать исполняемые файлы")
        if extension not in required_members:
            return
        if not required_members[extension].issubset(members):
            raise FileValidationError(f"Содержимое файла не соответствует .{extension}")

    def _validate_file_signature(self, extension: str, file_bytes: bytes) -> None:
        if file_bytes.startswith(EXECUTABLE_FILE_SIGNATURES):
            raise FileValidationError("Исполняемые файлы запрещены")
        starts_with = {
            "pdf": (b"%PDF-",),
            "doc": (OLE_COMPOUND_FILE_HEADER,),
            "xls": (OLE_COMPOUND_FILE_HEADER,),
            "ppt": (OLE_COMPOUND_FILE_HEADER,),
            "jpg": (b"\xff\xd8\xff",),
            "jpeg": (b"\xff\xd8\xff",),
            "png": (b"\x89PNG\r\n\x1a\n",),
            "gif": (b"GIF87a", b"GIF89a"),
            "ogg": (b"OggS",),
            "webm": (b"\x1aE\xdf\xa3",),
        }
        if extension in starts_with and not file_bytes.startswith(
            starts_with[extension]
        ):
            raise FileValidationError(f"Содержимое файла не соответствует .{extension}")
        if extension == "webp" and not (
            file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WEBP"
        ):
            raise FileValidationError("Содержимое файла не соответствует .webp")
        if extension == "wav" and not (
            file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WAVE"
        ):
            raise FileValidationError("Содержимое файла не соответствует .wav")
        if extension == "mp3" and not (
            file_bytes.startswith(b"ID3")
            or (
                len(file_bytes) >= 2
                and file_bytes[0] == 0xFF
                and file_bytes[1] & 0xE0 == 0xE0
            )
        ):
            raise FileValidationError("Содержимое файла не соответствует .mp3")
        if extension in {"m4a", "mp4", "mov"} and file_bytes[4:8] != b"ftyp":
            raise FileValidationError(f"Содержимое файла не соответствует .{extension}")
        if extension in {"zip", "docx", "xlsx", "pptx"}:
            self._validate_zip_structure(file_bytes, extension)
        if extension in {"txt", "csv"}:
            if b"\x00" in file_bytes:
                raise FileValidationError(
                    f"Содержимое файла не соответствует .{extension}"
                )
            try:
                file_bytes.decode("utf-8")
            except UnicodeDecodeError as error:
                raise FileValidationError(
                    f"Содержимое файла не соответствует .{extension}"
                ) from error

    def validate_attachment(
        self, file_bytes: bytes, *, filename: str, content_type: str | None = None
    ) -> tuple[str, str]:
        """Проверить тип, размер и содержимое вложения до его загрузки в S3."""
        if not file_bytes:
            raise FileValidationError("Нельзя загрузить пустой файл")
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise FileValidationError("Размер одного файла не должен превышать 100 MiB")

        normalized_filename, extension = self._validate_filename(filename)
        detected_content_type = self._validate_content_type(extension, content_type)
        self._validate_file_signature(extension, file_bytes)
        return normalized_filename, detected_content_type

    def _build_path(self, category: str, object_id: str, filename: str) -> str:
        # сохраняем файлы по категориям, чтобы не путать разные типы загрузок
        return build_storage_key_path(category, object_id, filename)

    def _build_content_disposition(self, filename: str) -> str:
        sanitized = filename.replace("\n", "").replace("\r", "").strip() or "download"
        encoded = quote(sanitized, safe="")
        return f"attachment; filename*=UTF-8''{encoded}"

    def _get_client(self):
        url = self.endpoint_url
        use_ssl = str(url).startswith("https://")
        session = self._get_session()
        return session.client(
            "s3",
            endpoint_url=url,
            region_name=self.region_name,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            use_ssl=use_ssl,
            config=self._boto_config,
        )

    async def is_available(self) -> bool:
        """Проверить доступ к настроенному bucket без изменения его содержимого."""
        try:
            async with self._get_client() as s3:  # type: ignore[attr-defined]
                await s3.head_bucket(Bucket=self.bucket_name)
        except (BotoCoreError, ClientError) as error:
            logger.warning("S3 health check failed: %s", error)
            return False
        return True

    async def upload_bytes(
        self,
        file_bytes: bytes,
        *,
        category: str,
        object_id: str,
        filename: str,
        content_type: str | None = None,
        key: str | None = None,
    ) -> str:
        filename, detected_content_type = self.validate_attachment(
            file_bytes, filename=filename, content_type=content_type
        )
        if key is None:
            if not category or not object_id or not filename:
                raise ValueError(
                    "category/object_id/filename обязательны при отсутствии key"
                )
            key = self._build_path(category, object_id, filename)

        async with self._get_client() as s3:  # type: ignore[attr-defined]
            try:
                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=BytesIO(file_bytes),
                    ACL="private",
                    ContentLength=len(file_bytes),
                    ContentType=detected_content_type,
                )
                logger.info(f"✅ Файл загружен: {key}")
                return key
            except ClientError as e:
                logger.error(f"Ошибка загрузки: {e}")
                raise

    async def generate_presigned_url(
        self, key, expiration=3600, download_name: str | None = None
    ):
        async with self._get_client() as s3:  # type: ignore[attr-defined]
            try:
                params = {"Bucket": self.bucket_name, "Key": key}
                if download_name:
                    params["ResponseContentDisposition"] = (
                        self._build_content_disposition(download_name)
                    )
                return await s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params=params,
                    ExpiresIn=expiration,
                )
            except ClientError as e:
                logger.error(f"Ошибка при генерации ссылки: {e}")
                return None

    async def delete_file(self, key):
        async with self._get_client() as s3:  # type: ignore[attr-defined]
            try:
                await s3.delete_object(Bucket=self.bucket_name, Key=key)
                logger.info(f"🗑️ Файл удалён: {key}")
            except ClientError as e:
                logger.error(f"Ошибка при удалении файла: {e}")
                raise

    async def download_bytes(self, key: str) -> bytes:
        async with self._get_client() as s3:  # type: ignore[attr-defined]
            try:
                response = await s3.get_object(Bucket=self.bucket_name, Key=key)
                body = response["Body"]
                return await body.read()
            except ClientError as e:
                logger.error(f"Ошибка при чтении файла: {e}")
                raise
