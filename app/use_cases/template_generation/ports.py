from typing import Any, Protocol
from uuid import UUID

from app.domain.templates import Template, TemplateTypes

from .dto import (
    GeneratedDocument,
    GenerationParameters,
    ShiftData,
    TemplateGenerateCommand,
)


class TemplateGenerator(Protocol):
    def generate(self, command: TemplateGenerateCommand) -> GeneratedDocument: ...


class GenerationTemplateRepository(Protocol):
    def get(self, template_id: UUID) -> Template: ...
    def get_default(self, template_type: TemplateTypes) -> Template | None: ...


class TemplateURLProvider(Protocol):
    def presigned_url(self, key: str) -> str: ...


class DocumentDataRepository(Protocol):
    def works(self) -> list[dict[str, Any]]: ...
    def shifts(
        self, parameters: GenerationParameters, start: int | None, end: int | None
    ) -> list[ShiftData]: ...
    def users(self, ids: tuple[UUID, ...]) -> list[dict[str, Any]]: ...
    def projects(self, ids: tuple[UUID, ...]) -> list[dict[str, Any]]: ...
    def leaves(self, user: UUID, start: int, end: int) -> list[dict[str, Any]]: ...


class DocumentDataSerializer(Protocol):
    def serialize(
        self, template_type: TemplateTypes, data: dict[str, Any]
    ) -> dict[str, Any]: ...


class DocumentDataBuilder(Protocol):
    def execute(
        self, kind: TemplateTypes, parameters: GenerationParameters
    ) -> dict[str, Any]: ...
