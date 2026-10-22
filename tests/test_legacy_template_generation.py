from types import SimpleNamespace

import pytest
import requests
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_restx import Api

from app.adapters.template_generation.legacy_http_client import (
    LegacyHTTPTemplateGenerator,
)
from app.use_cases.template_generation.legacy import LegacyTemplateGenerateCommand
from app.web.template_generation import legacy_routes, routes
from tests.test_template_use_case import case
from tests.test_template_web import headers


@pytest.fixture
def legacy_web(monkeypatch):
    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY="test-secret-key-with-at-least-32-bytes",
        TEMPLATE_SERVICE_OLD_URL="http://old:5000/legacy-path",
        TEMPLATE_SERVICE_NEW_URL="http://new:8000/api/docs/generate",
        TEMPLATE_SERVICE_API_KEY="new-key",
    )
    JWTManager(app)
    Api(app).add_namespace(routes.template_ns)
    calls = []

    def post(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(ok=True, content=b"legacy-file")

    monkeypatch.setattr(requests, "post", post)
    return app, app.test_client(), calls


def payload(**overrides):
    return {
        "name": "Legacy",
        "file_name": "legacy.docx",
        "document_data": {"nested": [1, {"key": None}]},
        **overrides,
    }


@pytest.mark.parametrize("role", ["admin", "manager", "user", "project-leader"])
@pytest.mark.parametrize("is_pdf", [False, True])
def test_historical_roles_response_and_payload(legacy_web, role, is_pdf):
    app, client, calls = legacy_web
    result = client.post(
        "/templates/generate",
        headers=headers(app, role),
        json=payload(is_pdf=is_pdf, ignored="field"),
    )
    assert result.status_code == 200
    assert result.data == b"legacy-file"
    assert (
        result.content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert result.headers["Content-Disposition"] == "attachment; filename=output.docx"
    assert calls == [
        {
            "url": app.config["TEMPLATE_SERVICE_OLD_URL"],
            "json": payload(is_pdf=is_pdf),
            "timeout": 120,
        }
    ]


@pytest.mark.parametrize(
    "source",
    [
        {"url": "https://source.test/file.docx"},
        {"url": None, "file_name": "legacy.docx"},
        {"url": "", "file_name": "legacy.docx"},
        {"url": "https://source.test/file.docx", "file_name": "legacy.docx"},
    ],
)
def test_legacy_source_variants_and_default_pdf(legacy_web, source):
    app, client, calls = legacy_web
    data = {"name": "", "document_data": {}, **source}
    result = client.post("/templates/generate", headers=headers(app, "user"), json=data)
    assert result.status_code == 200
    assert calls[0]["json"] == {
        "is_pdf": False,
        **{k: v for k, v in data.items() if v is not None},
    }


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"template_type": "work_types"},
        {"name": "Test", "document_data": {}},
        payload(file_name=None),
        payload(file_name=""),
        payload(document_data=None),
        payload(document_data=[]),
        payload(document_data="invalid"),
        payload(is_pdf=None),
        payload(is_pdf="bad"),
        {"file_name": "x", "document_data": {}},
        {"file_name": "x", "name": "Test"},
        [],
    ],
)
def test_invalid_legacy_requests_do_not_call_service(legacy_web, data):
    app, client, calls = legacy_web
    assert (
        client.post(
            "/templates/generate", headers=headers(app, "user"), json=data
        ).status_code
        == 400
    )
    assert calls == []


def test_legacy_missing_body_and_authentication(legacy_web):
    app, client, calls = legacy_web
    result = client.post("/templates/generate", headers=headers(app, "user"))
    assert result.status_code == 400
    assert result.json == {"msg": "Request body is required"}
    assert client.post("/templates/generate", json=payload()).status_code == 401
    assert calls == []


@pytest.mark.parametrize(
    "failure", ["missing_url", "network", "status", "timeout", "type", "value"]
)
def test_legacy_service_errors_keep_json_500(legacy_web, monkeypatch, failure):
    app, client, _calls = legacy_web
    if failure == "missing_url":
        app.config["TEMPLATE_SERVICE_OLD_URL"] = None
    else:

        def post(**kwargs):
            if failure == "network":
                raise requests.ConnectionError("unavailable")
            if failure == "timeout":
                assert kwargs["timeout"] == 120
                raise requests.Timeout("internal timeout details")
            if failure == "type":
                raise TypeError("internal serialization details")
            if failure == "value":
                raise ValueError("internal serialization details")
            return SimpleNamespace(ok=False)

        monkeypatch.setattr(requests, "post", post)
    result = client.post(
        "/templates/generate", headers=headers(app, "user"), json=payload()
    )
    assert result.status_code == 500
    assert result.json == {"msg": "Ошибка при генерации файла"}


@pytest.mark.parametrize("status", [200, 201, 202])
def test_legacy_accepts_historical_success_statuses(monkeypatch, status):
    response = requests.Response()
    response.status_code = status
    response._content = b"file"
    monkeypatch.setattr(requests, "post", lambda **kwargs: response)
    command = LegacyTemplateGenerateCommand(None, "x.docx", "Test", False, {})
    assert (
        LegacyHTTPTemplateGenerator("http://old/full/path").generate(command) == b"file"
    )


def test_new_and_old_clients_have_independent_urls_and_keys(legacy_web):
    app, _, _ = legacy_web
    with app.app_context():
        old = legacy_routes._generator()
        new = routes._generator()
    assert old.service_url == "http://old:5000/legacy-path"
    assert new.service_url == "http://new:8000/api/docs/generate"
    assert new.api_key == "new-key"


def test_routes_do_not_fallback_to_each_other(legacy_web, monkeypatch):
    app, client, calls = legacy_web
    dependencies, use_case = case()
    monkeypatch.setattr(routes, "_use_case", lambda: use_case)
    assert (
        client.post(
            "/templates/generate-new", headers=headers(app, "admin"), json=payload()
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/templates/generate",
            headers=headers(app, "admin"),
            json={"template_type": "work_types"},
        ).status_code
        == 400
    )
    assert dependencies.command is None
    assert calls == []
    result = client.post(
        "/templates/generate-new",
        headers=headers(app, "admin"),
        json={"template_type": "work_types"},
    )
    assert result.status_code == 200
    assert result.data == b"result"
    assert calls == []


def test_swagger_has_distinct_generation_contracts(legacy_web):
    app, _, _ = legacy_web
    # Obtain schema through the actual Swagger endpoint.
    schema = app.test_client().get("/swagger.json").json
    old_model = schema["paths"]["/templates/generate"]["post"]["parameters"][0][
        "schema"
    ]["$ref"]
    new_model = schema["paths"]["/templates/generate-new"]["post"]["parameters"][0][
        "schema"
    ]["$ref"]
    assert old_model != new_model
    assert (
        schema["paths"]["/templates/generate"]["post"]["operationId"]
        != schema["paths"]["/templates/generate-new"]["post"]["operationId"]
    )
    assert set(schema["definitions"][old_model.split("/")[-1]]["required"]) == {
        "name",
        "document_data",
    }
    assert schema["definitions"][new_model.split("/")[-1]]["required"] == [
        "template_type"
    ]


@pytest.mark.parametrize("error_type", [TypeError, ValueError])
def test_use_case_errors_return_generic_500(legacy_web, monkeypatch, error_type):
    app, client, calls = legacy_web

    def execute(self, command):
        raise error_type("internal use case details")

    monkeypatch.setattr(legacy_routes.LegacyGenerateTemplateUseCase, "execute", execute)
    result = client.post(
        "/templates/generate", headers=headers(app, "user"), json=payload()
    )
    assert result.status_code == 500
    assert result.json == {"msg": "Ошибка при генерации файла"}
    assert calls == []
