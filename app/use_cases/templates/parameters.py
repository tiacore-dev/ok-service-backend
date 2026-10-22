from dataclasses import dataclass
from typing import Any, Protocol

from app.domain.templates import TemplateTypes


@dataclass(frozen=True, slots=True)
class TemplateParameters:
    template_type: TemplateTypes
    parameters: list[str]
    schema: dict[str, Any]


class TemplateParametersProvider(Protocol):
    def describe(self, template_type: TemplateTypes) -> TemplateParameters: ...


@dataclass(slots=True)
class GetTemplateParametersUseCase:
    provider: TemplateParametersProvider

    def execute(self, template_type: TemplateTypes) -> TemplateParameters:
        return self.provider.describe(template_type)
