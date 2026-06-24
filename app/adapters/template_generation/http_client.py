from __future__ import annotations

from dataclasses import dataclass

import requests

from app.domain.template_generation import TemplateGenerationError
from app.use_cases.template_generation import (
    TemplateGenerateCommand,
    TemplateGenerator,
)


@dataclass(slots=True)
class HTTPTemplateGenerator(TemplateGenerator):
    service_url: str | None

    def generate(self, command: TemplateGenerateCommand) -> bytes:
        if not self.service_url:
            raise TemplateGenerationError("Template service URL is not configured.")

        payload: dict[str, object] = {
            "name": command.name,
            "is_pdf": command.is_pdf,
            "document_data": command.document_data,
        }
        if command.url is not None:
            payload["url"] = command.url
        if command.file_name is not None:
            payload["file_name"] = command.file_name

        try:
            response = requests.post(url=self.service_url, json=payload)
        except requests.RequestException as exc:
            raise TemplateGenerationError("Error while generating file.") from exc

        if not response.ok:
            raise TemplateGenerationError("Error while generating file.")

        return response.content
