from uuid import uuid4

from app.adapters.attachments.view import list_attachment_view_data
from app.domain.attachments import Attachment


class FakeAttachmentRepository:
    def __init__(self, attachment):
        self.attachment = attachment

    def list_attachments(self, target_type, target_id):
        assert target_type == "project"
        assert target_id == self.attachment.created_by
        return [self.attachment]


class FakeAttachmentStorage:
    def download_url(self, key, *, filename):
        return f"https://s3.test/{key}?filename={filename}"


def test_list_attachment_view_data_includes_preview_url():
    project_id = uuid4()
    attachment = Attachment(
        attachment_id=uuid4(),
        name="document.pdf",
        s3_key="ok-service/projects/project/document.pdf",
        file_size=123,
        checksum="checksum",
        meta={"content_type": "application/pdf", "extension": "pdf"},
        created_at=123456,
        created_by=project_id,
    )

    result = list_attachment_view_data(
        "project",
        project_id,
        repository=FakeAttachmentRepository(attachment),  # type: ignore[arg-type]
        storage=FakeAttachmentStorage(),  # type: ignore[arg-type]
    )

    assert result[0]["attachment_id"] == str(attachment.attachment_id)
    download_url = result[0]["download_url"]
    assert isinstance(download_url, str)
    assert download_url.startswith("https://s3.test/")


def test_list_attachment_view_data_returns_empty_list_without_attachments():
    class EmptyRepository:
        def list_attachments(self, target_type, target_id):
            return []

    result = list_attachment_view_data(
        "project",
        uuid4(),
        repository=EmptyRepository(),  # type: ignore[arg-type]
        storage=FakeAttachmentStorage(),  # type: ignore[arg-type]
    )

    assert result == []
