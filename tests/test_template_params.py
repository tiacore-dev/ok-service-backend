import json
from uuid import uuid4

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from flask_restx import Api
from jsonschema import Draft202012Validator, FormatChecker

from app.adapters.templates.parameters import MarshmallowTemplateParametersProvider
from app.domain.templates import TemplateTypes
from app.schemas.template_data_schemas import template_data_schema
from app.use_cases.templates.parameters import GetTemplateParametersUseCase
from app.web.templates import routes


@pytest.fixture
def params_web(monkeypatch):
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
    JWTManager(app)
    Api(app).add_namespace(routes.template_files_ns)

    def unexpected_io():
        raise AssertionError("Parameter catalog must not access templates or S3")

    monkeypatch.setattr(routes, "_use_case", unexpected_io)
    return app, app.test_client()


def auth_headers(app, role):
    with app.app_context():
        token = create_access_token(
            identity=json.dumps({"user_id": str(uuid4()), "role": role})
        )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("kind", list(TemplateTypes))
def test_catalog_schema_examples_paths_and_aliases(kind):
    result = GetTemplateParametersUseCase(
        MarshmallowTemplateParametersProvider()
    ).execute(kind)
    assert result.template_type == kind
    assert result.parameters and len(result.parameters) == len(set(result.parameters))
    schema = result.schema
    assert schema["title"] == kind.label()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(
        schema["example"]
    )
    assert template_data_schema(kind).load(schema["example"])
    for path in result.parameters:
        node = schema
        for segment in path.split("."):
            node = node["properties"][segment]
        assert node["title"] and "example" in node
        # Aliases are navigational only and must not introduce duplicate paths.
        assert not path.endswith("[i]")
    assert "$ref" not in json.dumps(schema)


def test_deep_paths_nullable_fields_and_validation_constraints():
    provider = MarshmallowTemplateParametersProvider()
    result = provider.describe(TemplateTypes.PAYROLL)
    assert {
        "parameters",
        "parameters.user.name",
        "user.name",
        "data",
        "data[i].date",
        "data[i].leave[i].reason",
        "data[i].shift_report[i].shift_report_details[i].work.name",
        "total_summ",
    } <= set(result.parameters)
    days = result.schema["properties"]["data"]
    assert days["example"][0]["date"] == "2026-10-05"
    assert "data[i]" not in result.schema["example"]
    day_properties = days["items"]["properties"]
    assert "shift_report[i]" in day_properties
    assert set(day_properties["leave"]["items"]["properties"]["reason"]["enum"]) == {
        "vacation",
        "sick_leave",
        "day_off",
    }
    single = provider.describe(TemplateTypes.SHIFT_REPORT)
    report_properties = single.schema["properties"]["shift_report"]["properties"]
    position = report_properties["shift_report_details"]["items"]["properties"][
        "project_work"
    ]
    assert position["type"] == ["object", "null"]
    assert position["example"]["project_work_id"]
    work = provider.describe(TemplateTypes.WORK_TYPES)
    category = work.schema["properties"]["works"]["items"]["properties"]["work_prices"][
        "items"
    ]["properties"]["category"]
    assert category["minimum"] == 0 and category["maximum"] == 4
    assert "data[i].leave" not in single.parameters
    obj = provider.describe(TemplateTypes.OBJECT_REPORT)
    assert "objects[i].projects[i].materials[i].material.material_id" in obj.parameters


@pytest.mark.parametrize("kind,path", [
    (TemplateTypes.SHIFT_REPORT_LIST, "shift_reports[i].modified_browser_id"),
    (TemplateTypes.SHIFT_REPORT, "shift_report.modified_browser_id"),
    (TemplateTypes.PAYROLL, "data[i].shift_report[i].modified_browser_id"),
])
def test_catalog_includes_modified_browser_id(kind, path):
    result = MarshmallowTemplateParametersProvider().describe(kind)
    assert path in result.parameters
    node = result.schema
    for segment in path.split("."):
        node = node["properties"][segment]
    assert node["type"] == ["string", "null"]
    assert node["format"] == "uuid"
    assert node["example"] is None


def test_catalog_calls_do_not_share_mutable_descriptions():
    provider = MarshmallowTemplateParametersProvider()
    result = provider.describe(TemplateTypes.WORK_TYPES)
    result.schema["properties"]["works[i]"]["title"] = "changed"
    assert result.schema["properties"]["works"]["items"]["title"] != "changed"
    result.parameters.clear()
    result.schema.clear()
    assert provider.describe(TemplateTypes.WORK_TYPES).parameters


@pytest.mark.parametrize("kind", list(TemplateTypes))
@pytest.mark.parametrize("role", ["admin", "manager"])
def test_params_endpoint(params_web, kind, role):
    app, client = params_web
    response = client.get(
        "/templates/params",
        query_string={"template_type": kind.value},
        headers=auth_headers(app, role),
    )
    assert response.status_code == 200
    assert set(response.json) == {"template_type", "parameters", "schema"}
    assert response.json["template_type"] == kind.value
    assert response.json["schema"]["title"] == kind.label()


@pytest.mark.parametrize(
    "query",
    [
        "",
        "template_type=",
        "template_type=invalid",
        "template_type=Виды работ",
        "template_type=payroll&extra=1",
        "template_type=payroll&template_type=work_types",
    ],
)
def test_params_query_validation(params_web, query):
    app, client = params_web
    assert (
        client.get(
            f"/templates/params?{query}", headers=auth_headers(app, "admin")
        ).status_code
        == 400
    )


@pytest.mark.parametrize(
    "role,status", [(None, 401), ("user", 403), ("project-leader", 403)]
)
def test_params_authorization(params_web, role, status):
    app, client = params_web
    assert (
        client.get(
            "/templates/params?template_type=payroll",
            headers=auth_headers(app, role) if role else {},
        ).status_code
        == status
    )


def test_params_swagger_contract(params_web):
    _, client = params_web
    schema = client.get("/swagger.json").json
    operation = schema["paths"]["/templates/params"]["get"]
    query = operation["parameters"][0]
    assert query["name"] == "template_type" and query["required"]
    assert query["enum"] == [value.value for value in TemplateTypes]
    assert set(schema["definitions"]["StoredTemplateParams"]["properties"]) == {
        "template_type",
        "parameters",
        "schema",
    }
