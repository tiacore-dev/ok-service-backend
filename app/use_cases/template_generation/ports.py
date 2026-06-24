from __future__ import annotations

from typing import Protocol

from .dto import TemplateGenerateCommand


class TemplateGenerator(Protocol):
    def generate(self, command: TemplateGenerateCommand) -> bytes: ...
