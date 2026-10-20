import json
from dataclasses import replace
from uuid import uuid4

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from flask_restx import Api

from app.domain.template_generation import TemplateGenerationError
from app.domain.templates import (
    TemplateNotFoundError,
    TemplateStorageError,
    TemplateTypes,
)
from app.schemas.template_schemas import TemplateGenerateSchema
from app.use_cases.template_generation.dto import GeneratedDocument
from app.web.template_generation import routes
from tests.test_template_data_schemas import object_result
from tests.test_template_use_case import case


@pytest.fixture
def generation_web(monkeypatch):
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = "test-secret-key-with-at-least-32-bytes"
    JWTManager(app)
    Api(app).add_namespace(routes.template_ns)
    dependencies, use_case = case()
    monkeypatch.setattr(routes, "_use_case", lambda: use_case)
    return app, app.test_client(), dependencies


@pytest.fixture
def generation_logs(caplog, monkeypatch):
    # create_app configures a non-propagating logger in the full suite.
    # Capture this logger directly, exactly once, in both test modes.
    monkeypatch.setattr(routes.logger, "propagate", False)
    routes.logger.addHandler(caplog.handler)
    try:
        yield caplog
    finally:
        routes.logger.removeHandler(caplog.handler)


def headers(app, role):
    with app.app_context():
        token = create_access_token(
            identity=json.dumps({"user_id": str(uuid4()), "role": role})
        )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    "role,status",
    [("admin", 200), ("manager", 200), ("user", 403), ("project-leader", 403)],
)
def test_generation_role_gate(generation_web, role, status):
    app, client, dependencies = generation_web
    result = client.post(
        "/templates/generate",
        headers=headers(app, role),
        json={"template_type": "work_types"},
    )
    assert result.status_code == status
    if status == 200:
        assert result.data == b"result"
        assert result.content_type == "application/pdf"
    else:
        assert dependencies.command is None


def test_generation_requires_authentication(generation_web):
    _, client, dependencies = generation_web
    assert (
        client.post(
            "/templates/generate", json={"template_type": "work_types"}
        ).status_code
        == 401
    )
    assert dependencies.command is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"template_type": "unknown"},
        {"template_type": "work_types", "template_id": "bad"},
        {"template_type": "work_types", "template_id": None},
        {"template_type": "work_types", "is_pdf": None, "parameters": None},
        {"template_type": "work_types", "parameters": {"user": str(uuid4())}},
        {"template_type": "work_types", "url": "https://external.test"},
        {"template_type": "work_types", "document_data": {}},
        {"template_type": "shift_report"},
        {"template_type": "shift_report", "parameters": {"shift_report_id": "bad"}},
        {
            "template_type": "payroll",
            "parameters": {"date_from": "2026-10-05", "date_to": "2026-10-06"},
        },
        {
            "template_type": "payroll",
            "parameters": {
                "date_from": "2026-10-07",
                "date_to": "2026-10-06",
                "user": str(uuid4()),
            },
        },
        {"template_type": "object_report"},
        {
            "template_type": "object_report",
            "parameters": {"date_from": "bad", "date_to": "2026-10-06"},
        },
        {
            "template_type": "object_report",
            "parameters": {
                "date_from": "2026-10-05",
                "date_to": "2026-10-06",
                "users": None,
            },
        },
        {
            "template_type": "object_report",
            "parameters": {
                "date_from": "2026-10-05",
                "date_to": "2026-10-06",
                "projects": str(uuid4()),
            },
        },
    ],
)
def test_invalid_requests_return_400_without_generation(generation_web, payload):
    app, client, dependencies = generation_web
    result = client.post(
        "/templates/generate", headers=headers(app, "admin"), json=payload
    )
    assert result.status_code == 400, result.json
    assert dependencies.command is None


@pytest.mark.parametrize("kind", ["payroll", "object_report", "shift_report_list"])
def test_maximum_period_end_returns_400_before_template_lookup(generation_web, kind):
    app, client, dependencies = generation_web
    parameters = {"date_from": "9999-12-31", "date_to": "9999-12-31"}
    if kind == "payroll":
        parameters["user"] = str(uuid4())
    response = client.post(
        "/templates/generate",
        headers=headers(app, "admin"),
        json={"template_type": kind, "parameters": parameters},
    )
    assert response.status_code == 400
    payload = object_result(response.get_json())
    assert "9999-12-30" in payload["errors"]["parameters"]["date_to"][0]
    assert dependencies.reads == []
    assert dependencies.command is None


@pytest.mark.parametrize(
    "kind,parameters",
    [
        ("work_types", {}),
        ("shift_report", {"shift_report_id": str(uuid4())}),
        (
            "payroll",
            {"date_from": "2026-10-05", "date_to": "2026-10-06", "user": str(uuid4())},
        ),
        (
            "object_report",
            {
                "date_from": "2026-10-05",
                "date_to": "2026-10-06",
                "users": [],
                "projects": [],
            },
        ),
    ],
)
def test_valid_parameters_are_normalized(kind, parameters):
    data = object_result(
        TemplateGenerateSchema().load({"template_type": kind, "parameters": parameters})
    )
    assert data["template_type"] == TemplateTypes(kind)
    if "date_from" in parameters:
        assert data["parameters"]["date_from"].isoformat() == parameters["date_from"]


def test_generation_missing_default_and_mismatched_type(generation_web):
    app, client, dependencies = generation_web
    dependencies.template = replace(
        dependencies.template, template_type=TemplateTypes.PAYROLL
    )
    result = client.post(
        "/templates/generate",
        headers=headers(app, "manager"),
        json={"template_type": "work_types"},
    )
    assert result.status_code == 400
    assert "не совпадает" in result.json["msg"]
    dependencies.template = None
    result = client.post(
        "/templates/generate",
        headers=headers(app, "manager"),
        json={"template_type": "work_types"},
    )
    assert result.status_code == 400
    assert "нет дефолтного шаблона" in result.json["msg"]


@pytest.mark.parametrize(
    "error,status",
    [
        (TemplateGenerationError(), 500),
        (TemplateNotFoundError(), 404),
        (TemplateStorageError(), 503),
    ],
)
def test_generation_errors(generation_web, monkeypatch, generation_logs, error, status):
    app, client, _ = generation_web

    class Failure:
        def execute(self, command):
            raise error

    monkeypatch.setattr(routes, "_use_case", Failure)
    result = client.post(
        "/templates/generate",
        headers=headers(app, "admin"),
        json={"template_type": "work_types"},
    )
    assert result.status_code == status
    failures = [
        record
        for record in generation_logs.records
        if record.name == "ok_service" and record.exc_info
    ]
    if status in {500, 503}:
        assert len(failures) == 1
        assert failures[0].exc_info[1] is error
        assert failures[0].getMessage() == (
            "Template generation failed"
            if status == 500
            else "Template storage request failed during generation"
        )
    else:
        assert failures == []


def test_generation_requires_body(generation_web):
    app, client, _ = generation_web
    result = client.post("/templates/generate", headers=headers(app, "admin"))
    assert result.status_code == 400
    assert result.json == {"msg": "Request body is required"}


def test_response_streams_and_closes_upstream(generation_web, monkeypatch):
    app, client, _ = generation_web
    state = []

    def chunks():
        state.append("first")
        yield b"first"
        state.append("second")
        yield b"second"

    class Stream:
        def execute(self, command):
            return GeneratedDocument(
                chunks(),
                "application/pdf",
                "attachment; filename=report.pdf",
                lambda: state.append("closed"),
            )

    monkeypatch.setattr(routes, "_use_case", Stream)
    result = client.post(
        "/templates/generate",
        headers=headers(app, "admin"),
        json={"template_type": "work_types"},
        buffered=False,
    )
    assert state == ["first"]
    assert result.headers["Content-Disposition"] == "attachment; filename=report.pdf"
    assert result.data == b"firstsecond"
    result.close()
    assert state == ["first", "second", "closed"]


def test_all_template_routes_share_swagger_group(generation_web):
    _, client, _ = generation_web
    schema = client.get("/swagger.json").json
    assert "template_files" not in {tag["name"] for tag in schema["tags"]}
    paths = {
        path: methods
        for path, methods in schema["paths"].items()
        if path.startswith("/templates/")
    }
    assert len(paths) == 9
    for methods in paths.values():
        for method, operation in methods.items():
            if method in {"get", "post", "patch", "delete"}:
                assert operation["tags"] == ["templates"]


@pytest.mark.parametrize(
    "parameters",
    [
        {},
        {"date_from": "2026-10-05"},
        {"date_to": "2026-10-05"},
        {"date_from": None, "date_to": "2026-10-05"},
        {"date_from": "2026-02-30", "date_to": "2026-10-05"},
        {"date_from": "2026-10-06", "date_to": "2026-10-05"},
        *[
            {"date_from": "2026-10-05", "date_to": "2026-10-05", field: value}
            for field in ("users", "projects")
            for value in (None, str(uuid4()), ["bad-uuid"])
        ],
        {"date_from": "2026-10-05", "date_to": "2026-10-05", "user": str(uuid4())},
    ],
)
def test_registry_invalid_parameters_return_400_before_reading_templates(
    generation_web, parameters
):
    app, client, dependencies = generation_web
    response = client.post(
        "/templates/generate",
        headers=headers(app, "admin"),
        json={
            "template_type": "shift_report_list",
            "parameters": parameters,
        },
    )
    assert response.status_code == 400, response.json
    assert "parameters" in response.json["errors"]
    assert dependencies.reads == []
    assert dependencies.command is None


@pytest.mark.parametrize(
    "filters",
    [
        {},
        {"users": [], "projects": []},
        {"users": [str(uuid4())], "projects": [str(uuid4())]},
    ],
)
@pytest.mark.parametrize("empty", [False, True])
def test_registry_generates_file_with_normalized_period_and_filters(
    generation_web, monkeypatch, filters, empty
):
    from datetime import date
    from uuid import UUID

    from app.adapters.template_generation.data_repository import (
        MarshmallowDocumentDataSerializer,
    )
    from app.use_cases.template_generation import GenerateTemplateUseCase
    from app.use_cases.template_generation.build_data import (
        BuildDocumentData,
        period_bounds,
    )
    from tests.test_template_generation_data import Repository

    app, client, dependencies = generation_web
    repository = Repository()
    if empty:
        repository.reports = []
    dependencies.template = replace(
        dependencies.template, template_type=TemplateTypes.SHIFT_REPORT_LIST
    )
    use_case = GenerateTemplateUseCase(
        dependencies,
        dependencies,
        dependencies,
        BuildDocumentData(repository, MarshmallowDocumentDataSerializer()),
    )
    monkeypatch.setattr(routes, "_use_case", lambda: use_case)
    response = client.post(
        "/templates/generate",
        headers=headers(app, "manager"),
        json={
            "template_type": "shift_report_list",
            "parameters": {
                "date_from": "2026-10-05",
                "date_to": "2026-10-05",
                **filters,
            },
        },
    )
    assert response.status_code == 200, response.data
    assert response.data == b"result"
    assert repository.query is not None
    parameters, start, end = repository.query
    assert (start, end) == period_bounds(date(2026, 10, 5), date(2026, 10, 5))
    assert parameters.users == tuple(UUID(value) for value in filters.get("users", []))
    assert parameters.projects == tuple(
        UUID(value) for value in filters.get("projects", [])
    )
    rows = dependencies.command.document_data["shift_reports"]
    assert len(rows) == (0 if empty else 1)
    if rows:
        assert "shift_report_details" not in rows[0]
        assert "shift_report_materials" not in rows[0]


def test_invalid_backend_print_data_returns_generic_500_and_logs_cause(
    generation_web, monkeypatch, generation_logs
):
    from marshmallow import ValidationError

    from app.adapters.template_generation.data_repository import (
        MarshmallowDocumentDataSerializer,
    )
    from app.use_cases.template_generation import GenerateTemplateUseCase
    from app.use_cases.template_generation.build_data import BuildDocumentData
    from tests.test_template_generation_data import Repository

    app, client, dependencies = generation_web
    repository = Repository()
    repository.reports[0].details[0]["work"]["name"] = None
    use_case = GenerateTemplateUseCase(
        dependencies,
        dependencies,
        dependencies,
        BuildDocumentData(repository, MarshmallowDocumentDataSerializer()),
    )
    monkeypatch.setattr(routes, "_use_case", lambda: use_case)
    response = client.post(
        "/templates/generate",
        headers=headers(app, "admin"),
        json={"template_type": "work_types"},
    )
    assert response.status_code == 500
    assert response.json == {"msg": "Ошибка при генерации файла"}
    assert dependencies.command is None
    failures = [
        record
        for record in generation_logs.records
        if record.name == "ok_service" and record.exc_info
    ]
    assert len(failures) == 1
    failure = failures[0]
    assert failure.getMessage() == "Template generation failed"
    error = failure.exc_info[1]
    assert isinstance(error, TemplateGenerationError)
    assert isinstance(error.__cause__, ValidationError)
    assert "name" in str(error.__cause__.messages)
