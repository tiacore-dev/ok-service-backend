from typing import TypedDict


class TemplateChanges(TypedDict, total=False):
    name: str
    description: str | None
    output_file_name: str | None
    is_horizontal: bool
    is_pdf: bool
    is_default: bool


class TemplateFileChanges(TemplateChanges, total=False):
    s3_key: str
    file_name: str
    content_type: str
