"""Report selection and calculations shared by generation of all template types."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.domain.template_generation.period import validate_report_period_end
from app.domain.templates import TemplateTypes

from .dto import GenerationParameters, ShiftData
from .ports import DocumentDataRepository, DocumentDataSerializer

REPORT_TIMEZONE = ZoneInfo("Asia/Novosibirsk")
ZERO = Decimal(0)


def day_of(timestamp: int) -> date:
    return datetime.fromtimestamp(timestamp / 1000, REPORT_TIMEZONE).date()


def period_bounds(start: date, end: date) -> tuple[int, int]:
    validate_report_period_end(end)
    return (
        int(datetime.combine(start, time.min, REPORT_TIMEZONE).timestamp() * 1000),
        int(
            datetime.combine(
                end + timedelta(days=1), time.min, REPORT_TIMEZONE
            ).timestamp()
            * 1000
        ),
    )


def estimated(quantity: Decimal, position: dict[str, Any] | None) -> Decimal | None:
    if position is None or position["price"] is None:
        return None
    return quantity * position["price"]


def printable_shift(
    source: ShiftData, *, details: bool = False, materials: bool = False
) -> dict[str, Any]:
    rows = [
        dict(row, summ_by_estimate=estimated(row["quantity"], row["project_work"]))
        for row in source.details
    ]
    result = dict(source.registry)
    result["shift_report_details_sum"] = sum((row["summ"] for row in rows), ZERO)
    result["shift_report_details_summ_by_estimate"] = sum(
        (
            row["summ_by_estimate"]
            for row in rows
            if row["summ_by_estimate"] is not None
        ),
        ZERO,
    )
    if details:
        result["shift_report_details"] = rows
    if materials:
        result["shift_report_materials"] = [
            dict(
                row,
                summ_by_estimate=estimated(row["quantity"], row["project_material"]),
            )
            for row in source.materials
        ]
    return result


@dataclass(slots=True)
class BuildDocumentData:
    repository: DocumentDataRepository
    serializer: DocumentDataSerializer

    def execute(
        self, kind: TemplateTypes, parameters: GenerationParameters
    ) -> dict[str, Any]:
        if kind == TemplateTypes.WORK_TYPES:
            data = {"works": self.repository.works()}
        elif kind == TemplateTypes.SHIFT_REPORT:
            if parameters.shift_report_id is None:
                raise ValueError("Для shift_report требуется shift_report_id")
            reports = self.repository.shifts(parameters, None, None)
            if not reports:
                raise ValueError("Смена не найдена или недоступна для печати")
            data = {
                "shift_report": printable_shift(
                    reports[0], details=True, materials=True
                )
            }
        else:
            if parameters.date_from is None or parameters.date_to is None:
                raise ValueError("Для отчёта требуется период date_from/date_to")
            if parameters.date_from > parameters.date_to:
                raise ValueError("Конец периода не может быть раньше начала")
            start, end = period_bounds(parameters.date_from, parameters.date_to)
            if kind == TemplateTypes.PAYROLL:
                data = self._payroll(parameters, start, end)
            elif kind == TemplateTypes.OBJECT_REPORT:
                data = self._objects(parameters, start, end)
            elif kind == TemplateTypes.SHIFT_REPORT_LIST:
                data = {
                    "shift_reports": [
                        printable_shift(row)
                        for row in self.repository.shifts(parameters, start, end)
                    ]
                }
            else:
                raise ValueError("Неизвестный тип шаблона")
        return self.serializer.serialize(kind, data)

    def _payroll(
        self, parameters: GenerationParameters, start: int, end: int
    ) -> dict[str, Any]:
        if parameters.user is None:
            raise ValueError("Для ведомости требуется user")
        user = self.repository.users((parameters.user,))[0]
        reports = self.repository.shifts(parameters, start, end)
        leaves = self.repository.leaves(parameters.user, start, end)
        by_day: dict[date, list[dict[str, Any]]] = {}
        total = ZERO
        for report in reports:
            row = printable_shift(report, details=True)
            by_day.setdefault(day_of(row["date"]), []).append(row)
            total += row["shift_report_details_summ_by_estimate"]
        days = []
        current, last = parameters.date_from, parameters.date_to
        assert current is not None and last is not None
        while current <= last:
            days.append(
                {
                    "date": current,
                    "leave": [
                        row
                        for row in leaves
                        if day_of(row["start_date"])
                        <= current
                        <= day_of(row["end_date"])
                    ],
                    "shift_report": by_day.get(current, []),
                }
            )
            current += timedelta(days=1)
        return {
            "parameters": {
                "date_from": parameters.date_from,
                "date_to": parameters.date_to,
                "user": user,
            },
            "user": user,
            "data": days,
            "total_summ": total,
        }

    def _objects(
        self, parameters: GenerationParameters, start: int, end: int
    ) -> dict[str, Any]:
        users = self.repository.users(parameters.users)
        projects = self.repository.projects(parameters.projects)
        objects: dict[Any, dict[str, Any]] = {}
        for report in self.repository.shifts(parameters, start, end):
            registry = report.registry
            object_id = registry["object"]["object_id"]
            project_id = registry["project"]["project_id"]
            obj = objects.setdefault(object_id, dict(registry["object"], projects={}))
            project = obj["projects"].setdefault(
                project_id, dict(registry["project"], works={}, materials={})
            )
            for detail in report.details:
                position = detail["project_work"]
                if position is None:
                    continue
                row = project["works"].setdefault(
                    position["project_work_id"],
                    {
                        "project_work": position,
                        "work": detail["work"],
                        "quantity": ZERO,
                        "summ": ZERO,
                    },
                )
                row["quantity"] += detail["quantity"]
                cost = estimated(detail["quantity"], position)
                row["summ"] += cost if cost is not None else ZERO
            for material in report.materials:
                position = material["project_material"]
                catalog = position["material"]
                row = project["materials"].setdefault(
                    catalog["material_id"],
                    {
                        "material": catalog,
                        "quantity": ZERO,
                        "summ": ZERO,
                    },
                )
                row["quantity"] += material["quantity"]
                cost = estimated(material["quantity"], position)
                row["summ"] += cost if cost is not None else ZERO
        result = []
        for _, obj in sorted(objects.items(), key=lambda item: str(item[0])):
            projects_out = []
            for _, project in sorted(
                obj["projects"].items(), key=lambda item: str(item[0])
            ):
                for section in ("works", "materials"):
                    project[section] = [
                        row
                        for _, row in sorted(
                            project[section].items(), key=lambda item: str(item[0])
                        )
                    ]
                if project["works"] or project["materials"]:
                    projects_out.append(project)
            if projects_out:
                result.append(dict(obj, projects=projects_out))
        return {
            "parameters": {
                "date_from": parameters.date_from,
                "date_to": parameters.date_to,
                "users": users,
                "projects": projects,
            },
            "objects": result,
        }
