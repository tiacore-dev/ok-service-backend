from dataclasses import dataclass
from uuid import UUID


class AttachmentError(Exception):
    """Base error for attachment workflows."""


class AttachmentNotFoundError(AttachmentError):
    pass


class AttachmentForbiddenError(AttachmentError):
    pass


class AttachmentConflictError(AttachmentError):
    pass


class AttachmentStorageError(AttachmentError):
    pass


@dataclass(frozen=True, slots=True)
class AttachmentTarget:
    target_type: str
    target_id: UUID
    deleted: bool
    owner_id: UUID | None = None
    project_leader_id: UUID | None = None
    signed: bool = False
    leave_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class Attachment:
    attachment_id: UUID
    name: str
    s3_key: str
    file_size: int
    checksum: str
    meta: dict[str, str]
    created_at: int
    created_by: UUID
