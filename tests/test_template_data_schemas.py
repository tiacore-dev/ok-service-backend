import json
from copy import deepcopy
from datetime import date
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from marshmallow import Schema, ValidationError, fields

from app.domain.templates import TemplateTypes
from app.schemas.template_data_schemas import (
    TEMPLATE_DATA_SCHEMAS,
    ObjectReportRequestSchema,
    PayrollRequestSchema,
    PeriodSchema,
    template_data_schema,
)


def object_result(result: object) -> dict[str, Any]:
    """Narrow Marshmallow's dict/list/None result for single-object contracts."""
    assert isinstance(result, dict), "Expected a single schema object"
    return cast(dict[str, Any], result)


@pytest.mark.parametrize("result", [None, [], "invalid"])
def test_object_result_rejects_non_object_schema_results(result):
    with pytest.raises(AssertionError, match="Expected a single schema object"):
        object_result(result)


def example(schema: Schema) -> dict[str, Any]:
    """Build a complete example recursively from the contract metadata."""
    result = {}
    for name, field in schema.fields.items():
        if isinstance(field, fields.Nested) and not field.allow_none:
            result[name] = example(field.schema)
        elif isinstance(field, fields.List) and isinstance(field.inner, fields.Nested):
            result[name] = [example(field.inner.schema)]
        else:
            result[name] = deepcopy(field.metadata["example"])
    return result


def array_item_schema(schema: Schema, name: str) -> Schema:
    field = schema.fields[name]
    assert isinstance(field, fields.List)
    assert isinstance(field.inner, fields.Nested)
    return field.inner.schema


@pytest.mark.parametrize("kind", list(TemplateTypes))
def test_all_five_contracts_load_dump_json_and_metadata(kind):
    schema = template_data_schema(kind.value)
    assert type(schema) is TEMPLATE_DATA_SCHEMAS[kind]
    payload = example(schema)
    if kind == TemplateTypes.PAYROLL:
        # Nullable leave is expanded only for demonstrating absence data.
        payload["data"][0]["leave"][0]["comment"] = None
    normalized = object_result(schema.load(payload))
    output = object_result(schema.dump(normalized))
    assert json.loads(json.dumps(output, allow_nan=False)) == output
    assert output == payload

    def check_metadata(current):
        for field in current.fields.values():
            assert field.metadata["title"]
            assert "example" in field.metadata
            if isinstance(field, fields.Nested):
                check_metadata(field.schema)
            elif isinstance(field, fields.List) and isinstance(
                field.inner, fields.Nested
            ):
                check_metadata(field.inner.schema)

    check_metadata(schema)


def test_registry_covers_existing_list_fields_without_details():
    schema = template_data_schema(TemplateTypes.SHIFT_REPORT_LIST)
    row = array_item_schema(schema, "shift_reports")
    from app.routes.models.shift_report_models import shift_report_model

    # user/project are expanded for printing; object contains object_name.
    expected = set(shift_report_model) - {"project_name", "object_name"}
    assert set(row.fields) == expected | {"object"}
    assert "shift_report_details" not in row.fields
    assert "shift_report_materials" not in row.fields


@pytest.mark.parametrize("browser_id", [None, str(uuid4())])
def test_registry_modified_browser_id_roundtrip(browser_id):
    schema = template_data_schema(TemplateTypes.SHIFT_REPORT_LIST)
    payload = example(schema)
    payload["shift_reports"][0]["modified_browser_id"] = browser_id
    assert object_result(schema.dump(schema.load(payload))) == payload


def test_registry_modified_browser_id_rejects_invalid_uuid():
    schema = template_data_schema(TemplateTypes.SHIFT_REPORT_LIST)
    payload = example(schema)
    payload["shift_reports"][0]["modified_browser_id"] = "invalid"
    with pytest.raises(ValidationError):
        schema.load(payload)


def test_single_shift_has_details_and_current_project_material_relationship():
    schema = template_data_schema("shift_report")
    payload = example(schema)
    report = payload["shift_report"]
    assert set(report).issuperset({"shift_report_details", "shift_report_materials"})
    material = report["shift_report_materials"][0]
    assert "project_material" in material
    assert "material" not in material
    assert "material" in material["project_material"]
    # A linked specification position may be absent in a detailed shift.
    assert report["shift_report_details"][0]["project_work"] is None
    assert schema.load(payload)


def test_payroll_preserves_daily_shape_parameters_and_estimate_total():
    schema = template_data_schema("payroll")
    payload = example(schema)
    payload["data"] = [
        {"date": "2026-10-05", "leave": [], "shift_report": []},
        {"date": "2026-10-06", "leave": [], "shift_report": []},
    ]
    report = example(
        array_item_schema(array_item_schema(schema, "data"), "shift_report")
    )
    report["shift_report_details_summ_by_estimate"] = 12345.67
    payload["data"][0]["shift_report"] = [report]
    payload["total_summ"] = Decimal("12345.67")
    loaded = object_result(schema.load(payload))
    dumped = object_result(schema.dump(loaded))
    assert dumped["data"] == payload["data"]
    assert dumped["total_summ"] == 12345.67
    assert dumped["parameters"]["user"] == dumped["user"]
    assert isinstance(dumped["total_summ"], float)
    assert (
        "shift_report_materials"
        not in array_item_schema(
            array_item_schema(schema, "data"), "shift_report"
        ).fields
    )


def test_object_report_has_separate_work_and_material_sections_without_shifts():
    schema = template_data_schema("object_report")
    payload = example(schema)
    project = payload["objects"][0]["projects"][0]
    assert set(project) == {"project_id", "name", "works", "materials"}
    assert "shift_reports" not in project
    work = project["works"][0]
    assert "project_work" in work and "work" in work
    assert work["project_work"] is not None
    material = project["materials"][0]
    assert set(material) == {"material", "quantity", "summ"}
    # A material group can cover multiple specification rows/prices.
    assert "price" not in material and "project_material" not in material
    assert schema.dump(schema.load(payload)) == payload
    work["project_work"] = None
    with pytest.raises(ValidationError):
        schema.load(payload)


def test_zero_total_and_nullable_prices_remain_distinct():
    schema = template_data_schema("payroll")
    payload = example(schema)
    payload["data"] = [
        {"date": "2026-10-05", "leave": [], "shift_report": []},
        {"date": "2026-10-06", "leave": [], "shift_report": []},
    ]
    payload["total_summ"] = Decimal("0.00")
    assert object_result(schema.dump(schema.load(payload)))["total_summ"] == 0.0
    schema = template_data_schema("object_report")
    payload = example(schema)
    work = payload["objects"][0]["projects"][0]["works"][0]
    for price in (None, 0.0):
        work["project_work"]["price"] = price
        dumped = object_result(schema.dump(schema.load(payload)))
        assert (
            dumped["objects"][0]["projects"][0]["works"][0]["project_work"]["price"]
            == price
        )


@pytest.mark.parametrize(
    "kind,field",
    [
        ("work_types", "works"),
        ("shift_report_list", "shift_reports"),
        ("object_report", "objects"),
    ],
)
def test_empty_collections_supported(kind, field):
    schema = template_data_schema(kind)
    payload = example(schema)
    payload[field] = []
    assert object_result(schema.dump(schema.load(payload)))[field] == []


@pytest.mark.parametrize("kind", list(TemplateTypes))
def test_required_roots_and_unknown_fields_rejected(kind):
    schema = template_data_schema(kind)
    payload = example(schema)
    for key in payload:
        incomplete = dict(payload)
        del incomplete[key]
        with pytest.raises(ValidationError):
            schema.load(incomplete)
    with pytest.raises(ValidationError):
        schema.load({**payload, "password_hash": "private"})


def test_catalog_nested_private_user_and_non_finite_numbers_rejected():
    schema = template_data_schema("payroll")
    payload = example(schema)
    payload["user"]["password_hash"] = "private"
    with pytest.raises(ValidationError):
        schema.load(payload)
    del payload["user"]["password_hash"]
    for number in (float("nan"), float("inf"), float("-inf")):
        payload["total_summ"] = number
        with pytest.raises(ValidationError):
            schema.load(payload)


@pytest.mark.parametrize(
    "schema_type", [PeriodSchema, PayrollRequestSchema, ObjectReportRequestSchema]
)
def test_period_required_iso_dates_inclusive_and_ordered(schema_type):
    schema = schema_type()
    payload = {"date_from": "2026-10-05", "date_to": "2026-10-05"}
    if schema_type is PayrollRequestSchema:
        payload["user"] = "00000000-0000-0000-0000-000000000001"
    result = object_result(schema.load(payload))
    assert result["date_from"] == result["date_to"] == date(2026, 10, 5)
    for field, value in [
        ("date_from", None),
        ("date_to", "2026-10-04"),
        ("date_from", "2026-02-30"),
        ("date_to", 1791133200000),
        ("date_to", "9999-12-31"),
    ]:
        with pytest.raises(ValidationError):
            schema.load({**payload, field: value})
    for field in ("date_from", "date_to"):
        incomplete = dict(payload)
        del incomplete[field]
        with pytest.raises(ValidationError):
            schema.load(incomplete)


@pytest.mark.parametrize("schema_type", [PayrollRequestSchema, ObjectReportRequestSchema])
def test_period_accepts_last_supported_end_date(schema_type):
    payload = {"date_from": "9999-12-30", "date_to": "9999-12-30"}
    if schema_type is PayrollRequestSchema:
        payload["user"] = "00000000-0000-0000-0000-000000000001"
    result = object_result(schema_type().load(payload))
    assert result["date_to"] == date(9999, 12, 30)


@pytest.mark.parametrize(
    "value", [None, [], ["00000000-0000-0000-0000-000000000001"], "invalid"]
)
def test_payroll_requires_exactly_one_uuid(value):
    with pytest.raises(ValidationError):
        PayrollRequestSchema().load(
            {"date_from": "2026-10-05", "date_to": "2026-10-06", "user": value}
        )


def test_payroll_missing_user_and_object_optional_filter_arrays():
    period = {"date_from": "2026-10-05", "date_to": "2026-10-06"}
    with pytest.raises(ValidationError):
        PayrollRequestSchema().load(period)
    schema = ObjectReportRequestSchema()
    default_filters = object_result(schema.load(period))
    assert default_filters["users"] == default_filters["projects"] == []
    identifier = "00000000-0000-0000-0000-000000000001"
    result = object_result(
        schema.load({**period, "users": [identifier], "projects": [identifier]})
    )
    assert result["users"] == result["projects"] == [UUID(identifier)]
    for field in ("users", "projects"):
        for value in (None, identifier, ["bad"]):
            with pytest.raises(ValidationError):
                schema.load({**period, field: value})


def test_unknown_type_rejected_and_instances_do_not_share_fields():
    with pytest.raises(ValueError):
        template_data_schema("invalid")
    schema = template_data_schema("work_types")
    schema.fields.clear()
    assert "works" in template_data_schema("work_types").fields
