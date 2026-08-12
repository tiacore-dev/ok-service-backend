from io import BytesIO
from uuid import uuid4

from flask import Flask
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from config import Config
from app.use_cases.attachments import AttachmentActor
from app.web.attachments import routes


class FailingAttachmentUseCase:
    def upload(self, *args, **kwargs):
        raise RuntimeError("database failed")


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
