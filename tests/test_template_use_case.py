from dataclasses import dataclass

from app.use_cases.template_generation import (
    GenerateTemplateUseCase,
    TemplateGenerateCommand,
)


@dataclass
class FakeTemplateGenerator:
    command: TemplateGenerateCommand | None = None

    def generate(self, command: TemplateGenerateCommand) -> bytes:
        self.command = command
        return b"generated-bytes"


def test_generate_template_use_case_delegates_to_generator():
    generator = FakeTemplateGenerator()
    command = TemplateGenerateCommand(
        url="https://example.test/template.docx",
        file_name=None,
        name="Invoice",
        is_pdf=False,
        document_data={"number": 1},
    )

    result = GenerateTemplateUseCase(generator=generator).execute(command)

    assert result == b"generated-bytes"
    assert generator.command == command
