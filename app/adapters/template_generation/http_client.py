from dataclasses import dataclass
from urllib.parse import quote

import requests

from app.domain.template_generation import TemplateGenerationError
from app.use_cases.template_generation.dto import (
    GeneratedDocument,
    TemplateGenerateCommand,
)


@dataclass(slots=True)
class HTTPTemplateGenerator:
    service_url: str | None
    api_key: str | None = None
    timeout: float = 30

    def generate(self, command: TemplateGenerateCommand) -> GeneratedDocument:
        if not self.service_url:
            raise TemplateGenerationError("Template service URL is not configured.")
        try:
            response = requests.post(
                url=self.service_url,
                json={
                    "url": command.url,
                    "name": command.name,
                    "is_pdf": command.is_pdf,
                    "is_horizontal": command.is_horizontal,
                    "document_data": command.document_data,
                },
                headers={"x-api-key": self.api_key} if self.api_key else {},
                timeout=self.timeout,
                stream=True,
            )
        except requests.RequestException as exc:
            raise TemplateGenerationError("Error while generating file.") from exc
        if response.status_code != 200:
            response.close()
            raise TemplateGenerationError("Error while generating file.")

        def chunks():
            try:
                yield from response.iter_content(chunk_size=64 * 1024)
            finally:
                response.close()

        return GeneratedDocument(
            chunks=chunks(),
            content_type=response.headers.get("Content-Type") or command.content_type,
            content_disposition=response.headers.get("Content-Disposition")
            or ("attachment; filename*=UTF-8''" + quote(command.filename, safe="")),
            close=response.close,
        )
