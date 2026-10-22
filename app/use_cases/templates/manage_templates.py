import logging
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.domain.templates import Template, TemplateTypes

from .dto import TemplateChanges, TemplateFileChanges
from .ports import TemplateRepository, TemplateStorage

logger = logging.getLogger("ok_service")


@dataclass(slots=True)
class TemplateUseCase:
    repository: TemplateRepository
    storage: TemplateStorage

    def _cleanup(self, key: str) -> None:
        try:
            self.storage.delete(key)
        except Exception:
            logger.exception("Failed to delete template S3 object: %s", key)

    def create(
        self,
        template_type: TemplateTypes,
        name: str,
        changes: TemplateChanges,
        content: bytes,
        filename: str,
        content_type: str | None,
    ) -> Template:
        template_id = uuid4()
        key, file_name, mime = self.storage.upload(
            template_id, content, filename, content_type
        )
        try:
            template = Template(
                id=template_id,
                name=name,
                template_type=template_type,
                s3_key=key,
                file_name=file_name,
                content_type=mime,
                description=changes.get("description"),
                output_file_name=changes.get("output_file_name"),
                is_horizontal=changes.get("is_horizontal", False),
                is_pdf=changes.get("is_pdf", False),
                is_default=changes.get("is_default", False),
            )
            self.repository.create(template)
        except Exception:
            self._cleanup(key)
            raise
        return template

    def get(self, template_id: UUID) -> Template:
        return self.repository.get(template_id)

    def list(
        self, template_type: TemplateTypes | None, offset: int, limit: int
    ) -> list[Template]:
        return self.repository.list(template_type, offset, limit)

    def update(
        self,
        template_id: UUID,
        changes: TemplateChanges,
        file: tuple[bytes, str, str | None] | None = None,
    ) -> Template:
        if not changes and file is None:
            raise ValueError("No data provided for update")
        self.repository.get(template_id)
        updates: TemplateFileChanges = {**changes}
        key = None
        if file is not None:
            key, file_name, mime = self.storage.upload(template_id, *file)
            updates.update(s3_key=key, file_name=file_name, content_type=mime)
        try:
            template, old_key = self.repository.update(template_id, updates)
        except Exception:
            if key is not None:
                self._cleanup(key)
            raise
        if old_key is not None:
            self._cleanup(old_key)
        return template

    def delete(self, template_id: UUID) -> None:
        template = self.repository.delete(template_id)
        self._cleanup(template.s3_key)

    def download(self, template_id: UUID) -> tuple[bytes, str, str]:
        template = self.repository.get(template_id)
        return (
            self.storage.download(template.s3_key),
            template.file_name,
            template.content_type,
        )
