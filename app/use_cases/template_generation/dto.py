from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class TemplateGenerateCommand:
    url: str | None
    file_name: str | None
    name: str
    is_pdf: bool
    document_data: dict[str, Any]
