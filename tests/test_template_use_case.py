from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.domain.templates import Template, TemplateNotFoundError, TemplateTypes
from app.use_cases.template_generation import GenerateTemplateUseCase
from app.use_cases.template_generation.dto import (
    GeneratedDocument,
    GenerateDocumentCommand,
    GenerationParameters,
    TemplateGenerateCommand,
)


class Dependencies:
    def __init__(self):
        self.template: Template | None = Template(
            id=uuid4(),
            name="Template",
            template_type=TemplateTypes.WORK_TYPES,
            s3_key="private/key",
            file_name="source.xlsx",
            content_type="application/test",
            is_pdf=True,
            is_horizontal=True,
        )
        self.command: TemplateGenerateCommand | None = None
        self.reads: list[UUID | TemplateTypes] = []

    def get(self, template_id: UUID) -> Template:
        self.reads.append(template_id)
        if self.template is None:
            raise TemplateNotFoundError("Template not found")
        return self.template

    def get_default(self, template_type: TemplateTypes) -> Template | None:
        self.reads.append(template_type)
        return self.template

    def presigned_url(self, key: str) -> str:
        assert key == "private/key"
        return "https://signed.test/file"

    def execute(
        self, kind: TemplateTypes, parameters: GenerationParameters
    ) -> dict[str, Any]:
        return {"works": []}

    def generate(self, command: TemplateGenerateCommand) -> GeneratedDocument:
        self.command = command
        return GeneratedDocument(
            [b"result"], command.content_type, command.filename, lambda: None
        )


def case():
    dependencies = Dependencies()
    return dependencies, GenerateTemplateUseCase(
        dependencies, dependencies, dependencies, dependencies
    )


@pytest.mark.parametrize(
    "is_pdf,extension", [(None, ".pdf"), (False, ".xlsx"), (True, ".pdf")]
)
def test_default_template_metadata_and_explicit_false(is_pdf, extension):
    deps, use_case = case()
    result = use_case.execute(
        GenerateDocumentCommand(TemplateTypes.WORK_TYPES, is_pdf=is_pdf)
    )
    assert list(result.chunks) == [b"result"]
    assert deps.reads == [TemplateTypes.WORK_TYPES]
    assert deps.command is not None
    assert deps.command.url == "https://signed.test/file"
    assert deps.command.filename == "source" + extension
    assert deps.command.is_horizontal is True
    assert deps.command.document_data == {"works": []}


def test_explicit_template_and_output_name():
    deps, use_case = case()
    assert deps.template is not None
    deps.template = replace(deps.template, output_file_name="Отчёт.xlsx")
    use_case.execute(
        GenerateDocumentCommand(TemplateTypes.WORK_TYPES, template_id=deps.template.id)
    )
    assert deps.reads == [deps.template.id]
    assert deps.command is not None
    assert deps.command.name == "Отчёт"
    assert deps.command.filename == "Отчёт.pdf"


def test_missing_default_template_is_validation_error():
    deps, use_case = case()
    deps.template = None
    with pytest.raises(ValueError, match="нет дефолтного шаблона"):
        use_case.execute(GenerateDocumentCommand(TemplateTypes.WORK_TYPES))
    assert deps.command is None


def test_template_type_mismatch_never_generates():
    deps, use_case = case()
    assert deps.template is not None
    with pytest.raises(ValueError, match="не совпадает"):
        use_case.execute(
            GenerateDocumentCommand(TemplateTypes.PAYROLL, template_id=deps.template.id)
        )
    assert deps.command is None
