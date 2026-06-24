from __future__ import annotations

from dataclasses import dataclass

from .dto import TemplateGenerateCommand
from .ports import TemplateGenerator


@dataclass(slots=True)
class GenerateTemplateUseCase:
    generator: TemplateGenerator

    def execute(self, command: TemplateGenerateCommand) -> bytes:
        return self.generator.generate(command)
