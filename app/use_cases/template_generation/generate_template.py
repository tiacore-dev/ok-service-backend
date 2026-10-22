from dataclasses import dataclass
from pathlib import PurePath

from .dto import GeneratedDocument, GenerateDocumentCommand, TemplateGenerateCommand
from .ports import (
    DocumentDataBuilder,
    GenerationTemplateRepository,
    TemplateGenerator,
    TemplateURLProvider,
)


@dataclass(slots=True)
class GenerateTemplateUseCase:
    generator: TemplateGenerator
    templates: GenerationTemplateRepository
    storage: TemplateURLProvider
    data_builder: DocumentDataBuilder

    def execute(self, command: GenerateDocumentCommand) -> GeneratedDocument:
        template = (
            self.templates.get(command.template_id)
            if command.template_id is not None
            else self.templates.get_default(command.template_type)
        )
        if template is None:
            raise ValueError("Для выбранного типа нет дефолтного шаблона")
        if template.template_type != command.template_type:
            raise ValueError("Тип шаблона не совпадает с переданным template_type")
        data = self.data_builder.execute(command.template_type, command.parameters)
        is_pdf = template.is_pdf if command.is_pdf is None else command.is_pdf
        # output_file_name is a literal name; template expressions are not evaluated.
        name = template.output_file_name or PurePath(template.file_name).stem
        suffix = PurePath(name).suffix.lower()
        if suffix in {".docx", ".xlsx", ".pdf"}:
            name = name[: -len(suffix)]
        extension = ".pdf" if is_pdf else PurePath(template.file_name).suffix.lower()
        content_type = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }[extension]
        return self.generator.generate(
            TemplateGenerateCommand(
                url=self.storage.presigned_url(template.s3_key),
                name=name,
                is_pdf=is_pdf,
                is_horizontal=template.is_horizontal,
                document_data=data,
                content_type=content_type,
                filename=name + extension,
            )
        )
