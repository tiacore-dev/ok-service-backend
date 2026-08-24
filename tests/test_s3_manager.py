import importlib.util
import zipfile
from asyncio import run
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from botocore.exceptions import EndpointConnectionError
from flask import Flask
from flask_restx import Api

import app.s3.s3_manager as s3_manager
from app.s3.s3_manager import AsyncS3Manager, FileValidationError, logger
from app.web.auth.routes import login_ns


def test_config_reads_s3_settings_from_environment(monkeypatch) -> None:
    expected_settings = {
        "ENDPOINT_URL": "http://s3.internal.example",
        "REGION_NAME": "ru-1",
        "AWS_ACCESS_KEY_ID": "access-key",
        "AWS_SECRET_ACCESS_KEY": "secret-key",
        "BUCKET_NAME": "ok-service",
    }
    for name, value in expected_settings.items():
        monkeypatch.setenv(name, value)

    config_path = Path(__file__).parents[1] / "config.py"
    spec = importlib.util.spec_from_file_location("s3_test_config", config_path)
    assert spec is not None and spec.loader is not None
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)

    for name, value in expected_settings.items():
        assert getattr(config_module.Config, name) == value


def test_s3_manager_uses_application_logger() -> None:
    assert logger.name == "ok_service"


@pytest.mark.parametrize(
    ("filename", "content", "content_type", "expected_content_type"),
    [
        ("document.pdf", b"%PDF-1.7", "application/pdf", "application/pdf"),
        (
            "photo.png",
            b"\x89PNG\r\n\x1a\nimage-data",
            "image/png",
            "image/png",
        ),
        ("notes.txt", "Текст".encode(), "text/plain", "text/plain"),
    ],
)
def test_validate_attachment_accepts_allowed_file_types(
    filename, content, content_type, expected_content_type
) -> None:
    normalized_filename, detected_content_type = AsyncS3Manager().validate_attachment(
        content, filename=filename, content_type=content_type
    )

    assert normalized_filename == filename
    assert detected_content_type == expected_content_type


def test_validate_attachment_accepts_zip_archive() -> None:
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("document.txt", "contents")

    _, content_type = AsyncS3Manager().validate_attachment(
        archive.getvalue(), filename="documents.zip", content_type="application/zip"
    )

    assert content_type == "application/zip"


def test_validate_attachment_rejects_disallowed_extension() -> None:
    with pytest.raises(FileValidationError, match="не поддерживаются"):
        AsyncS3Manager().validate_attachment(b"MZ", filename="program.exe")


def test_validate_attachment_rejects_path_in_filename() -> None:
    with pytest.raises(FileValidationError, match="не содержать пути"):
        AsyncS3Manager().validate_attachment(b"%PDF-1.7", filename="../document.pdf")


def test_validate_attachment_rejects_invalid_file_signature() -> None:
    with pytest.raises(FileValidationError, match="Исполняемые файлы запрещены"):
        AsyncS3Manager().validate_attachment(b"MZ", filename="program.pdf")


def test_validate_attachment_rejects_zip_with_executable_file() -> None:
    archive = BytesIO()
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("program.exe", b"MZ")

    with pytest.raises(FileValidationError, match="не должен содержать исполняемые"):
        AsyncS3Manager().validate_attachment(archive.getvalue(), filename="files.zip")


def test_validate_attachment_rejects_wrong_content_type() -> None:
    with pytest.raises(FileValidationError, match="MIME-тип"):
        AsyncS3Manager().validate_attachment(
            b"%PDF-1.7", filename="document.pdf", content_type="image/png"
        )


def test_validate_attachment_rejects_file_larger_than_limit(monkeypatch) -> None:
    monkeypatch.setattr(s3_manager, "MAX_FILE_SIZE_BYTES", 3)

    with pytest.raises(FileValidationError, match="100 MiB"):
        AsyncS3Manager().validate_attachment(b"1234", filename="notes.txt")


def test_s3_manager_reports_available_bucket(monkeypatch) -> None:
    class S3Client:
        async def head_bucket(self, *, Bucket):
            assert Bucket == "ok-service"

    class S3ClientContext:
        async def __aenter__(self):
            return S3Client()

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

    manager = AsyncS3Manager()
    manager.bucket_name = "ok-service"
    monkeypatch.setattr(manager, "_get_client", lambda: S3ClientContext())

    assert run(manager.is_available()) is True


def test_s3_manager_reports_unavailable_bucket_on_connection_error(monkeypatch) -> None:
    class S3Client:
        async def head_bucket(self, *, Bucket):
            raise EndpointConnectionError(endpoint_url="http://s3.internal.example")

    class S3ClientContext:
        async def __aenter__(self):
            return S3Client()

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

    manager = AsyncS3Manager()
    monkeypatch.setattr(manager, "_get_client", lambda: S3ClientContext())

    assert run(manager.is_available()) is False


def test_s3_health_endpoint_returns_ok_when_bucket_is_available(monkeypatch) -> None:
    async def is_available(_manager) -> bool:
        return True

    app = Flask(__name__)
    api = Api(app)
    api.add_namespace(login_ns)
    monkeypatch.setattr(AsyncS3Manager, "is_available", is_available)

    response = app.test_client().get("/auth/health/s3")

    assert response.status_code == 200
    assert response.json == {"service": "s3", "status": "ok"}


def test_s3_health_endpoint_returns_service_unavailable(monkeypatch) -> None:
    async def is_available(_manager) -> bool:
        return False

    app = Flask(__name__)
    api = Api(app)
    api.add_namespace(login_ns)
    monkeypatch.setattr(AsyncS3Manager, "is_available", is_available)

    response = app.test_client().get("/auth/health/s3")

    assert response.status_code == 503
    assert response.json == {"service": "s3", "status": "unavailable"}


def test_get_client_uses_internal_endpoint_for_storage_operations(monkeypatch) -> None:
    manager = AsyncS3Manager()
    manager.endpoint_url = "https://s3.internal.example"
    session = Mock()
    monkeypatch.setattr(manager, "_get_session", lambda: session)

    manager._get_client()

    session.client.assert_called_once_with(
        "s3",
        endpoint_url="https://s3.internal.example",
        region_name=manager.region_name,
        aws_access_key_id=manager.aws_access_key_id,
        aws_secret_access_key=manager.aws_secret_access_key,
        use_ssl=True,
        config=manager._boto_config,
    )


def test_generate_presigned_url_uses_single_storage_client(monkeypatch) -> None:
    class S3Client:
        async def generate_presigned_url(self, **kwargs):
            assert kwargs["Params"] == {"Bucket": "ok-service", "Key": "document.pdf"}
            return "https://s3.example/presigned-url"

    class S3ClientContext:
        async def __aenter__(self):
            return S3Client()

        async def __aexit__(self, exc_type, exc_value, traceback):
            return False

    manager = AsyncS3Manager()
    manager.bucket_name = "ok-service"
    get_client = Mock(return_value=S3ClientContext())
    monkeypatch.setattr(manager, "_get_client", get_client)

    result = run(manager.generate_presigned_url("document.pdf"))

    assert result == "https://s3.example/presigned-url"
    get_client.assert_called_once_with()
