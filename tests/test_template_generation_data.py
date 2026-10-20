from copy import deepcopy
from datetime import UTC, date
from decimal import Decimal as D
from uuid import uuid4

import pytest

from app.adapters.template_generation.data_repository import (
    MarshmallowDocumentDataSerializer,
)
from app.domain.templates import TemplateTypes
from app.schemas.template_data_schemas import ShiftReportFullPrintSchema
from app.use_cases.template_generation.build_data import (
    BuildDocumentData,
    period_bounds,
)
from app.use_cases.template_generation.dto import GenerationParameters, ShiftData
from tests.test_template_data_schemas import example, object_result


def shift():
    data = object_result(
        ShiftReportFullPrintSchema().load(example(ShiftReportFullPrintSchema()))
    )
    details = data.pop("shift_report_details")
    materials = data.pop("shift_report_materials")
    for key in ("shift_report_details_sum", "shift_report_details_summ_by_estimate"):
        data.pop(key)
    details[0].update(
        quantity=D("2.5"),
        summ=D(999),
        project_work={
            "project_work_id": uuid4(),
            "project_work_name": None,
            "price": D("3.33"),
        },
    )
    details[0].pop("summ_by_estimate")
    materials[0].update(quantity=D(3))
    materials[0]["project_material"]["price"] = D("2.1")
    materials[0].pop("summ_by_estimate")
    return ShiftData(data, details, materials)


class Repository:
    def __init__(self):
        self.reports = [shift()]
        self.absences = []
        self.query: tuple[GenerationParameters, int | None, int | None] | None = None

    def works(self):
        return [self.reports[0].details[0]["work"]]

    def shifts(self, parameters, start, end):
        self.query = (parameters, start, end)
        return self.reports

    def users(self, ids):
        return [
            dict(self.reports[0].registry["user"], user_id=identifier)
            for identifier in ids
        ]

    def projects(self, ids):
        return [
            dict(self.reports[0].registry["project"], project_id=identifier)
            for identifier in ids
        ]

    def leaves(self, user, start, end):
        return self.absences


def builder(repo):
    return BuildDocumentData(repo, MarshmallowDocumentDataSerializer())


def period(**kwargs):
    return GenerationParameters(
        date_from=date(2026, 10, 5), date_to=date(2026, 10, 7), **kwargs
    )


def test_single_shift_costs_schema_and_decimal_serialization():
    repo = Repository()
    result = builder(repo).execute(
        TemplateTypes.SHIFT_REPORT, GenerationParameters(shift_report_id=uuid4())
    )
    row = result["shift_report"]
    assert row["shift_report_details_summ_by_estimate"] == 8.325
    assert row["shift_report_details_sum"] == 999
    assert row["shift_report_materials"][0]["summ_by_estimate"] == 6.3
    assert isinstance(row["shift_report_id"], str)
    assert row["shift_report_details"][0]["project_work"]["project_work_name"] is None


def test_payroll_calendar_absences_no_materials_and_estimated_total():
    repo = Repository()
    start, end = period_bounds(date(2026, 10, 5), date(2026, 10, 7))
    repo.reports[0].registry["date"] = start
    repo.absences = [
        {
            "leave_id": uuid4(),
            "start_date": start - 86400000,
            "end_date": start + 86400000,
            "reason": "day_off",
            "reason_label": "Отгул",
            "comment": None,
        }
    ]
    result = builder(repo).execute(TemplateTypes.PAYROLL, period(user=uuid4()))
    assert [row["date"] for row in result["data"]] == [
        "2026-10-05",
        "2026-10-06",
        "2026-10-07",
    ]
    assert [len(row["leave"]) for row in result["data"]] == [1, 1, 0]
    assert [len(row["shift_report"]) for row in result["data"]] == [1, 0, 0]
    assert result["data"][0]["leave"][0]["start_date"] == start - 86400000
    assert "shift_report_materials" not in result["data"][0]["shift_report"][0]
    assert result["parameters"]["user"] == result["user"]
    assert result["total_summ"] == 8.325
    assert repo.query is not None
    assert repo.query[1:] == (start, end)


def test_objects_group_by_ids_and_each_material_price_and_omit_empty_projects():
    repo = Repository()
    first = repo.reports[0]
    second_material = deepcopy(first.materials[0])
    second_material["project_material"].update(project_material_id=uuid4(), price=D(10))
    second_material["quantity"] = D(2)
    first.materials.append(second_material)
    another_work = deepcopy(first.details[0])
    another_work["project_work"]["project_work_id"] = uuid4()
    first.details.append(another_work)  # same name, distinct position
    no_position = deepcopy(first.details[0])
    no_position["project_work"] = None
    first.details.append(no_position)
    second = ShiftData(
        dict(first.registry, project={"project_id": uuid4(), "name": "Empty"}),
        [no_position],
        [],
    )
    repo.reports.append(second)
    result = builder(repo).execute(TemplateTypes.OBJECT_REPORT, period())
    assert result["parameters"]["users"] == result["parameters"]["projects"] == []
    assert len(result["objects"]) == 1
    projects = result["objects"][0]["projects"]
    assert len(projects) == 1
    assert len(projects[0]["works"]) == 2
    assert projects[0]["materials"][0]["quantity"] == 5
    assert projects[0]["materials"][0]["summ"] == 26.3


def test_missing_prices_preserve_zero_quantities_and_material_only_project():
    repo = Repository()
    row = repo.reports[0]
    row.details.clear()
    row.materials[0]["quantity"] = D(0)
    row.materials[0]["project_material"]["price"] = None
    result = builder(repo).execute(
        TemplateTypes.OBJECT_REPORT, period(users=(uuid4(),), projects=(uuid4(),))
    )
    project = result["objects"][0]["projects"][0]
    assert project["works"] == []
    assert project["materials"][0]["quantity"] == project["materials"][0]["summ"] == 0
    assert (
        len(result["parameters"]["users"]) == len(result["parameters"]["projects"]) == 1
    )


def test_catalog_uses_its_own_schema():
    repo = Repository()
    result = builder(repo).execute(TemplateTypes.WORK_TYPES, GenerationParameters())
    assert list(result) == ["works"]
    assert result["works"][0]["work_id"] == str(
        repo.reports[0].details[0]["work"]["work_id"]
    )


@pytest.mark.parametrize("kind", [TemplateTypes.PAYROLL, TemplateTypes.OBJECT_REPORT])
def test_required_period_and_empty_results(kind):
    repo = Repository()
    with pytest.raises(ValueError, match="период"):
        builder(repo).execute(kind, GenerationParameters())
    repo.reports = []
    if kind == TemplateTypes.OBJECT_REPORT:
        assert builder(repo).execute(kind, period())["objects"] == []


def test_bounds_use_local_midnight_and_exclusive_end():
    from datetime import datetime

    start, end = period_bounds(date(2026, 10, 5), date(2026, 10, 5))
    assert (
        datetime.fromtimestamp(start / 1000, UTC).isoformat()
        == "2026-10-04T17:00:00+00:00"
    )
    assert end - start == 86400000


def test_bounds_accept_last_supported_period_end():
    start, end = period_bounds(date(9999, 12, 30), date(9999, 12, 30))
    assert end - start == 86400000


@pytest.mark.parametrize(
    "kind",
    [TemplateTypes.PAYROLL, TemplateTypes.OBJECT_REPORT, TemplateTypes.SHIFT_REPORT_LIST],
)
def test_maximum_date_rejected_before_reading_report_data(kind):
    repo = Repository()
    with pytest.raises(ValueError, match="9999-12-30"):
        builder(repo).execute(
            kind,
            GenerationParameters(
                date_from=date(9999, 12, 31),
                date_to=date(9999, 12, 31),
                user=uuid4() if kind == TemplateTypes.PAYROLL else None,
            ),
        )
    assert repo.query is None


@pytest.mark.parametrize("invalid", ["null_name", "missing_name", "invalid_category"])
def test_serializer_wraps_backend_validation_errors(invalid):
    from marshmallow import ValidationError

    from app.domain.template_generation import TemplateGenerationError
    from app.schemas.template_data_schemas import WorkTypesTemplateDataSchema

    data = example(WorkTypesTemplateDataSchema())
    work = data["works"][0]
    if invalid == "null_name":
        work["name"] = None
    elif invalid == "missing_name":
        del work["name"]
    else:
        work["work_prices"][0]["category"] = 99
    with pytest.raises(
        TemplateGenerationError, match="Printable data does not match"
    ) as caught:
        MarshmallowDocumentDataSerializer().serialize(TemplateTypes.WORK_TYPES, data)
    assert isinstance(caught.value.__cause__, ValidationError)


@pytest.mark.parametrize("result", [None, [], "invalid"])
def test_serializer_rejects_non_object_output(monkeypatch, result):
    from app.domain.template_generation import TemplateGenerationError

    class InvalidSchema:
        def dump(self, data):
            return result

    monkeypatch.setattr(
        "app.adapters.template_generation.data_repository.template_data_schema",
        lambda kind: InvalidSchema(),
    )
    with pytest.raises(
        TemplateGenerationError, match="Printable data must be an object"
    ):
        MarshmallowDocumentDataSerializer().serialize(TemplateTypes.WORK_TYPES, {})
