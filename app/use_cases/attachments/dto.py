from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class AttachmentActor:
    user_id: UUID
    role: str


@dataclass(frozen=True, slots=True)
class UploadFile:
    name: str
    content: bytes
    content_type: str | None
