from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class LegacyTemplateGenerateCommand:
    url: str | None
    file_name: str | None
    name: str
    is_pdf: bool
    document_data: dict[str, Any]


class LegacyTemplateGenerator(Protocol):
    def generate(self, command: LegacyTemplateGenerateCommand) -> bytes: ...


@dataclass(slots=True)
class LegacyGenerateTemplateUseCase:
    generator: LegacyTemplateGenerator

    def execute(self, command: LegacyTemplateGenerateCommand) -> bytes:
        return self.generator.generate(command)
