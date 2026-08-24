from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest

from app.domain.attachments import (
    Attachment,
    AttachmentForbiddenError,
    AttachmentTarget,
)
from app.use_cases.attachments import AttachmentActor, AttachmentUseCase, UploadFile
from app.use_cases.attachments.ports import AttachmentRepository, AttachmentStorage


@dataclass
class FakeRepository(AttachmentRepository):
    target: AttachmentTarget | None
    attachments: list[Attachment] = field(default_factory=list)
    fail_create: bool = False
    created_target: tuple[str, UUID] | None = None

    def get_target(self, target_type, target_id):
        return self.target

    def create_attachments(self, target_type, target_id, attachments):
        if self.fail_create:
            raise RuntimeError("database failed")
        self.created_target = (target_type, target_id)
        self.attachments.extend(attachments)

    def list_attachments(self, target_type, target_id):
        return list(self.attachments)

    def get_attachment(self, target_type, target_id, attachment_id):
        return next(
            (item for item in self.attachments if item.attachment_id == attachment_id),
            None,
        )

    def delete_attachment(self, target_type, target_id, attachment_id):
        attachment = self.get_attachment(target_type, target_id, attachment_id)
        if attachment is not None:
            self.attachments.remove(attachment)
        return attachment


@dataclass
class FakeStorage(AttachmentStorage):
    uploaded_keys: list[str] = field(default_factory=list)
    deleted_keys: list[str] = field(default_factory=list)

    def upload(
        self,
        content,
        *,
        target_type,
        target_id,
        attachment_id,
        filename,
        content_type,
    ):
        normalized_name = filename.replace(" ", "_")
        key = f"ok-service/{target_type}s/{target_id}/{attachment_id}_{normalized_name}"
        self.uploaded_keys.append(key)
        return key, normalized_name, content_type or "application/pdf"

    def delete(self, key):
        self.deleted_keys.append(key)

    def download_bytes(self, key):
        return b"file contents"


def _file(name="document.pdf"):
    return UploadFile(name=name, content=b"%PDF-1.7", content_type="application/pdf")


def test_upload_multiple_project_attachments_is_atomic_and_uses_project_folder():
    leader_id = uuid4()
    project_id = uuid4()
    repository = FakeRepository(
        AttachmentTarget(
            target_type="project",
            target_id=project_id,
            deleted=False,
            project_leader_id=leader_id,
        )
    )
    storage = FakeStorage()

    result = AttachmentUseCase(repository, storage).upload(
        "project",
        project_id,
        [_file("first file.pdf"), _file("second.pdf")],
        AttachmentActor(leader_id, "project-leader"),
    )

    assert len(result) == 2
    assert repository.created_target == ("project", project_id)
    assert all(f"ok-service/projects/{project_id}/" in key for key in storage.uploaded_keys)
    assert result[0].name == "first_file.pdf"
    assert len(result[0].checksum) == 64


def test_upload_compensates_s3_when_database_write_fails():
    actor_id = uuid4()
    repository = FakeRepository(
        AttachmentTarget("project", uuid4(), False), fail_create=True
    )
    storage = FakeStorage()
    target = repository.target
    assert target is not None

    with pytest.raises(RuntimeError, match="database failed"):
        AttachmentUseCase(repository, storage).upload(
            "project",
            target.target_id,
            [_file("first.pdf"), _file("second.pdf")],
            AttachmentActor(actor_id, "admin"),
        )

    assert storage.deleted_keys == storage.uploaded_keys


@pytest.mark.parametrize("role", ["admin", "manager"])
def test_admin_and_manager_can_upload_to_any_project(role):
    target = AttachmentTarget("project", uuid4(), False, project_leader_id=uuid4())
    use_case = AttachmentUseCase(FakeRepository(target), FakeStorage())

    assert use_case.upload(
        "project", target.target_id, [_file()], AttachmentActor(uuid4(), role)
    )


def test_project_leader_cannot_upload_to_another_project():
    target = AttachmentTarget("project", uuid4(), False, project_leader_id=uuid4())

    with pytest.raises(AttachmentForbiddenError):
        AttachmentUseCase(FakeRepository(target), FakeStorage()).upload(
            "project",
            target.target_id,
            [_file()],
            AttachmentActor(uuid4(), "project-leader"),
        )


def test_assigned_object_manager_can_upload_attachment():
    manager_id = uuid4()
    target = AttachmentTarget("object", uuid4(), False, owner_id=manager_id)

    result = AttachmentUseCase(FakeRepository(target), FakeStorage()).upload(
        "object", target.target_id, [_file()], AttachmentActor(manager_id, "manager")
    )

    assert len(result) == 1


def test_unassigned_object_manager_cannot_upload_attachment():
    target = AttachmentTarget("object", uuid4(), False, owner_id=uuid4())

    with pytest.raises(AttachmentForbiddenError):
        AttachmentUseCase(FakeRepository(target), FakeStorage()).upload(
            "object",
            target.target_id,
            [_file()],
            AttachmentActor(uuid4(), "manager"),
        )


def test_place_attachment_uses_related_object_manager_acl():
    manager_id = uuid4()
    target = AttachmentTarget("place", uuid4(), False, owner_id=manager_id)

    result = AttachmentUseCase(FakeRepository(target), FakeStorage()).upload(
        "place", target.target_id, [_file()], AttachmentActor(manager_id, "manager")
    )

    assert len(result) == 1


def test_unassigned_manager_cannot_upload_place_attachment():
    target = AttachmentTarget("place", uuid4(), False, owner_id=uuid4())

    with pytest.raises(AttachmentForbiddenError):
        AttachmentUseCase(FakeRepository(target), FakeStorage()).upload(
            "place", target.target_id, [_file()], AttachmentActor(uuid4(), "manager")
        )


@pytest.mark.parametrize("target_type", ["object", "place"])
@pytest.mark.parametrize("role", ["manager", "project-leader"])
def test_manager_and_project_leader_can_view_any_object_or_place_attachment(
    target_type, role
):
    attachment = Attachment(
        uuid4(),
        "document.pdf",
        "key",
        8,
        "checksum",
        {"content_type": "application/pdf", "extension": "pdf"},
        1,
        uuid4(),
    )
    target = AttachmentTarget(target_type, uuid4(), False, owner_id=uuid4())
    use_case = AttachmentUseCase(
        FakeRepository(target, attachments=[attachment]), FakeStorage()
    )
    actor = AttachmentActor(uuid4(), role)

    assert use_case.list(target_type, target.target_id, actor) == [attachment]
    content, filename, content_type = use_case.download_bytes(
        target_type, target.target_id, attachment.attachment_id, actor
    )
    assert (content, filename, content_type) == (
        b"file contents",
        "document.pdf",
        "application/pdf",
    )


@pytest.mark.parametrize("target_type", ["object", "place"])
@pytest.mark.parametrize("role", ["manager", "project-leader"])
def test_manager_and_project_leader_cannot_upload_to_foreign_object_or_place(
    target_type, role
):
    target = AttachmentTarget(target_type, uuid4(), False, owner_id=uuid4())

    with pytest.raises(AttachmentForbiddenError):
        AttachmentUseCase(FakeRepository(target), FakeStorage()).upload(
            target_type,
            target.target_id,
            [_file()],
            AttachmentActor(uuid4(), role),
        )


def test_user_can_upload_only_to_own_unsigned_shift_report():
    user_id = uuid4()
    target = AttachmentTarget("shift_report", uuid4(), False, owner_id=user_id)

    result = AttachmentUseCase(FakeRepository(target), FakeStorage()).upload(
        "shift_report", target.target_id, [_file()], AttachmentActor(user_id, "user")
    )

    assert len(result) == 1


@pytest.mark.parametrize(
    ("owner_matches", "signed"), [(False, False), (True, True)]
)
def test_user_cannot_upload_to_forbidden_shift_report(owner_matches, signed):
    user_id = uuid4()
    target = AttachmentTarget(
        "shift_report",
        uuid4(),
        False,
        owner_id=user_id if owner_matches else uuid4(),
        signed=signed,
    )

    with pytest.raises(AttachmentForbiddenError):
        AttachmentUseCase(FakeRepository(target), FakeStorage()).upload(
            "shift_report",
            target.target_id,
            [_file()],
            AttachmentActor(user_id, "user"),
        )


def test_user_can_list_and_download_own_signed_shift_report_attachment():
    user_id = uuid4()
    target = AttachmentTarget(
        "shift_report", uuid4(), False, owner_id=user_id, signed=True
    )
    attachment = Attachment(
        uuid4(),
        "approved.pdf",
        "key",
        8,
        "checksum",
        {"content_type": "application/pdf", "extension": "pdf"},
        1,
        user_id,
    )
    repository = FakeRepository(target, attachments=[attachment])
    use_case = AttachmentUseCase(repository, FakeStorage())

    assert use_case.list(
        "shift_report", target.target_id, AttachmentActor(user_id, "user")
    ) == [attachment]
    content, filename, content_type = use_case.download_bytes(
        "shift_report",
        target.target_id,
        attachment.attachment_id,
        AttachmentActor(user_id, "user"),
    )
    assert (content, filename, content_type) == (
        b"file contents",
        "approved.pdf",
        "application/pdf",
    )


@pytest.mark.parametrize("role", ["manager", "project-leader"])
def test_non_admin_cannot_edit_signed_shift_report_attachments(role):
    target = AttachmentTarget(
        "shift_report", uuid4(), False, owner_id=uuid4(), signed=True
    )

    with pytest.raises(AttachmentForbiddenError):
        AttachmentUseCase(FakeRepository(target), FakeStorage()).upload(
            "shift_report",
            target.target_id,
            [_file()],
            AttachmentActor(uuid4(), role),
        )


def test_user_can_delete_attachment_from_own_unsigned_shift_report():
    user_id = uuid4()
    target = AttachmentTarget("shift_report", uuid4(), False, owner_id=user_id)
    attachment = Attachment(
        uuid4(),
        "document.pdf",
        "key",
        8,
        "checksum",
        {"content_type": "application/pdf", "extension": "pdf"},
        1,
        user_id,
    )
    repository = FakeRepository(target, attachments=[attachment])

    AttachmentUseCase(repository, FakeStorage()).delete(
        "shift_report",
        target.target_id,
        attachment.attachment_id,
        AttachmentActor(user_id, "user"),
    )
    assert repository.attachments == []


def test_user_cannot_delete_attachment_from_own_signed_shift_report():
    user_id = uuid4()
    target = AttachmentTarget("shift_report", uuid4(), False, owner_id=user_id, signed=True)
    attachment = Attachment(
        uuid4(),
        "approved.pdf",
        "key",
        8,
        "checksum",
        {"content_type": "application/pdf", "extension": "pdf"},
        1,
        user_id,
    )
    repository = FakeRepository(target, attachments=[attachment])

    with pytest.raises(AttachmentForbiddenError):
        AttachmentUseCase(repository, FakeStorage()).delete(
            "shift_report",
            target.target_id,
            attachment.attachment_id,
            AttachmentActor(user_id, "user"),
        )
