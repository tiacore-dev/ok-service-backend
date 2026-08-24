from io import BytesIO
from uuid import uuid4

from flask import Flask, Response
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from config import Config
from app.use_cases.attachments import AttachmentActor
from app.web.attachments import routes


class FailingAttachmentUseCase:
    def upload(self, *args, **kwargs):
        raise RuntimeError("database failed")

    def download_bytes(self, *args, **kwargs):
        raise RuntimeError("storage failed")


def test_bad_multipart_request_returns_400():
    response, status = routes._error(BadRequest("Malformed multipart request"))

    assert status == 400
    assert response == {"msg": "400 Bad Request: Malformed multipart request"}


def test_oversized_multipart_request_returns_413():
    response, status = routes._error(RequestEntityTooLarge())

    assert status == 413
    assert response == {"msg": "413 Request Entity Too Large: The data value transmitted exceeds the capacity limit."}


def test_application_request_body_limit_allows_100_mib_file_with_multipart_overhead():
    assert Config.MAX_CONTENT_LENGTH == 105 * 1024 * 1024


def test_upload_logs_unexpected_exception_with_traceback(monkeypatch, caplog):
    app = Flask(__name__)
    actor = AttachmentActor(uuid4(), "admin")
    # The application logger intentionally disables propagation to avoid duplicate
    # production records; enable it here so pytest can inspect the LogRecord.
    monkeypatch.setattr(routes.logger, "propagate", True)
    monkeypatch.setattr(routes, "_actor", lambda: actor)
    monkeypatch.setattr(routes, "_use_case", lambda: FailingAttachmentUseCase())

    with app.test_request_context(
        "/shift_reports/62692922-bc80-4501-ac69-c387b3397f57/attachments",
        method="POST",
        data={"files": (BytesIO(b"file"), "document.txt")},
        content_type="multipart/form-data",
    ):
        with caplog.at_level("DEBUG", logger="ok_service"):
            response, status = routes._upload(
                "shift_report", "62692922-bc80-4501-ac69-c387b3397f57"
            )

    assert status == 500
    assert response == {"msg": "Internal server error"}
    assert "Attachment upload failed unexpectedly" in caplog.text
    assert "RuntimeError: database failed" in caplog.text
    assert "Traceback" in caplog.text


def test_download_uses_rfc5987_content_disposition_for_unicode_filename(monkeypatch):
    app = Flask(__name__)
    actor = AttachmentActor(uuid4(), "admin")

    class DownloadingAttachmentUseCase:
        def download_bytes(self, *args, **kwargs):
            return b"%PDF-1.7", "Заявление_на_возврат.pdf", "application/pdf"

    monkeypatch.setattr(routes, "_actor", lambda: actor)
    monkeypatch.setattr(routes, "_use_case", lambda: DownloadingAttachmentUseCase())

    with app.test_request_context(
        "/shift_reports/62692922-bc80-4501-ac69-c387b3397f57/attachments/"
        "62692922-bc80-4501-ac69-c387b3397f57/download",
        method="GET",
    ):
        response = routes._download(
            "shift_report",
            "62692922-bc80-4501-ac69-c387b3397f57",
            "62692922-bc80-4501-ac69-c387b3397f57",
        )

    assert isinstance(response, Response)
    assert response.status_code == 200
    assert response.headers["Content-Disposition"] == (
        "inline; filename=__.pdf; filename*=UTF-8''"
        "%D0%97%D0%B0%D1%8F%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D0%B5_%D0%BD%D0%B0_%D0%B2%D0%BE%D0%B7%D0%B2%D1%80%D0%B0%D1%82.pdf"
    )


def test_download_logs_unexpected_exception_with_traceback(monkeypatch, caplog):
    app = Flask(__name__)
    actor = AttachmentActor(uuid4(), "admin")
    monkeypatch.setattr(routes.logger, "propagate", True)
    monkeypatch.setattr(routes, "_actor", lambda: actor)
    monkeypatch.setattr(routes, "_use_case", lambda: FailingAttachmentUseCase())

    with app.test_request_context(
        "/shift_reports/62692922-bc80-4501-ac69-c387b3397f57/attachments/"
        "62692922-bc80-4501-ac69-c387b3397f57/download",
        method="GET",
    ):
        with caplog.at_level("DEBUG", logger="ok_service"):
            result = routes._download(
                "shift_report",
                "62692922-bc80-4501-ac69-c387b3397f57",
                "62692922-bc80-4501-ac69-c387b3397f57",
            )
            assert isinstance(result, tuple)
            response, status = result

    assert status == 500
    assert response == {"msg": "Internal server error"}
    assert "Attachment download failed unexpectedly" in caplog.text
    assert "RuntimeError: storage failed" in caplog.text
    assert "Traceback" in caplog.text
