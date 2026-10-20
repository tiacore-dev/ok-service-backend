from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import UUID

from app.domain.templates import TemplateTypes


@dataclass(frozen=True, slots=True)
class GenerationParameters:
    date_from: date | None = None
    date_to: date | None = None
    user: UUID | None = None
    users: tuple[UUID, ...] = ()
    projects: tuple[UUID, ...] = ()
    shift_report_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class GenerateDocumentCommand:
    template_type: TemplateTypes
    parameters: GenerationParameters = field(default_factory=GenerationParameters)
    template_id: UUID | None = None
    is_pdf: bool | None = None


@dataclass(frozen=True, slots=True)
class TemplateGenerateCommand:
    url: str
    name: str
    is_pdf: bool
    is_horizontal: bool
    document_data: dict[str, Any]
    content_type: str
    filename: str


@dataclass(slots=True)
class GeneratedDocument:
    chunks: Iterable[bytes]
    content_type: str
    content_disposition: str
    close: Callable[[], None]


@dataclass(frozen=True, slots=True)
class ShiftData:
    registry: dict[str, Any]
    details: list[dict[str, Any]]
    materials: list[dict[str, Any]]
