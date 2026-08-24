from uuid import UUID, uuid4

from app.adapters.attachments.view import list_attachment_view_data
from app.domain.attachments import Attachment


class FakeAttachmentRepository:
    def __init__(self, attachment: Attachment):
        self.attachment = attachment

    def list_attachments(self, target_type: str, target_id: UUID) -> list[Attachment]:
        assert target_type == "project"
        assert target_id == self.attachment.created_by
        return [self.attachment]


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
        repository=FakeAttachmentRepository(attachment),
    )

    assert result[0]["attachment_id"] == str(attachment.attachment_id)
    assert "download_url" not in result[0]


def test_list_attachment_view_data_returns_empty_list_without_attachments():
    class EmptyRepository:
        def list_attachments(
            self, target_type: str, target_id: UUID
        ) -> list[Attachment]:
            return []

    result = list_attachment_view_data(
        "project",
        uuid4(),
        repository=EmptyRepository(),
    )

    assert result == []


def test_list_attachment_view_data_supports_places():
    place_id = uuid4()

    class EmptyRepository:
        def list_attachments(
            self, target_type: str, target_id: UUID
        ) -> list[Attachment]:
            assert target_type == "place"
            assert target_id == place_id
            return []

    assert list_attachment_view_data("place", place_id, EmptyRepository()) == []
