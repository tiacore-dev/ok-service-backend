from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class TemplateTypes(str, Enum):
    WORK_TYPES = "work_types"
    SHIFT_REPORT = "shift_report"
    SHIFT_REPORT_LIST = "shift_report_list"
    PAYROLL = "payroll"
    OBJECT_REPORT = "object_report"

    def label(self) -> str:
        return {
            self.WORK_TYPES: "Виды работ",
            self.SHIFT_REPORT: "Отчет по смене",
            self.SHIFT_REPORT_LIST: "Отчет по смене - список",
            self.PAYROLL: "Зарплатная ведомость",
            self.OBJECT_REPORT: "Отчет по объектам",
        }[self]


DEFAULT_TEMPLATE_INDEX = "uq_templates_default_type"


class TemplateNotFoundError(Exception):
    pass


class TemplateConflictError(Exception):
    pass


class TemplateStorageError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Template:
    id: UUID
    name: str
    template_type: TemplateTypes
    s3_key: str
    file_name: str
    content_type: str
    description: str | None = None
    output_file_name: str | None = None
    is_horizontal: bool = False
    is_pdf: bool = False
    is_default: bool = False
