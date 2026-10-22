import json
from dataclasses import replace
from importlib.util import module_from_spec, spec_from_file_location
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4
from zipfile import ZipFile, ZipInfo

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from flask_restx import Api
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateIndex
from werkzeug.datastructures import MultiDict

from app.adapters.templates.s3_storage import S3TemplateStorage
from app.adapters.templates.sqlalchemy_repository import SQLAlchemyTemplateRepository
from app.database.models.templates import Templates
from app.domain.templates import (
    DEFAULT_TEMPLATE_INDEX,
    TemplateConflictError,
    TemplateNotFoundError,
    TemplateStorageError,
    TemplateTypes,
)
from app.s3.s3_manager import AsyncS3Manager, FileValidationError
from app.use_cases.templates.manage_templates import TemplateUseCase
from app.web.template_generation.routes import template_ns
from app.web.templates import routes


def office_file(extension="docx"):
    stream = BytesIO()
    fixed = (2020, 1, 1, 0, 0, 0)
    with ZipFile(stream, "w") as archive:
        archive.writestr(ZipInfo("[Content_Types].xml", fixed), "<Types/>")
        archive.writestr(
            ZipInfo(
                "word/document.xml" if extension == "docx" else "xl/workbook.xml", fixed
            ),
            "<root/>",
        )
    return stream.getvalue()


class FakeRepository:
    def __init__(self):
        self.items = {}
        self.fail = False

    def _check(self, template):
        if self.fail:
            raise RuntimeError("database failed")
        if template.is_default and any(
            other.id != template.id
            and other.template_type == template.template_type
            and other.is_default
            for other in self.items.values()
        ):
            raise TemplateConflictError(
                "Для этого типа уже назначен шаблон по умолчанию"
            )

    def create(self, template):
        self._check(template)
        self.items[template.id] = template

    def get(self, template_id):
        if template_id not in self.items:
            raise TemplateNotFoundError("Template not found")
        return self.items[template_id]

    def list(self, template_type, offset, limit):
        items = sorted(self.items.values(), key=lambda item: (item.name, item.id))
        return [
            item
            for item in items
            if template_type is None or item.template_type == template_type
        ][offset : offset + limit]

    def update(self, template_id, changes):
        old = self.get(template_id)
        item = replace(old, **changes)
        self._check(item)
        self.items[template_id] = item
        return item, old.s3_key if "s3_key" in changes else None

    def delete(self, template_id):
        item = self.get(template_id)
        if self.fail:
            raise RuntimeError("database failed")
        del self.items[template_id]
        return item


class FakeS3Manager(AsyncS3Manager):
    def __init__(self):
        self.objects = {}
        self.deleted = []
        self.fail_upload = False
        self.fail_delete = False

    async def upload_bytes(self, content, **kwargs):
        if self.fail_upload:
            raise OSError("S3 unavailable")
        self.objects[kwargs["key"]] = content
        return kwargs["key"]

    async def delete_file(self, key):
        if self.fail_delete:
            raise OSError("S3 unavailable")
        self.deleted.append(key)
        self.objects.pop(key, None)

    async def download_bytes(self, key):
        return self.objects[key]


@pytest.fixture
def setup():
    repository = FakeRepository()
    manager = FakeS3Manager()
    use_case = TemplateUseCase(repository, S3TemplateStorage(manager))
    return repository, manager, use_case


def create(use_case, **changes):
    template_type = changes.pop("template_type", TemplateTypes.WORK_TYPES)
    return use_case.create(
        template_type, "Шаблон", changes, office_file(), "Шаблон.docx", None
    )


def test_create_download_update_delete(setup):
    repository, manager, use_case = setup
    item = create(use_case, description="text", is_default=True)
    assert item.template_type is TemplateTypes.WORK_TYPES
    assert not item.is_pdf and not item.is_horizontal
    assert item.s3_key.startswith(f"ok-service/templates/{item.id}/")
    assert use_case.download(item.id)[:2] == (office_file(), "Шаблон.docx")
    updated = use_case.update(
        item.id,
        {"description": None, "is_default": False, "output_file_name": "report.xlsx"},
    )
    assert updated.description is None and updated.is_default is False
    assert updated.s3_key == item.s3_key and manager.deleted == []
    replacement = use_case.update(
        item.id, {}, (office_file("xlsx"), "report.xlsx", None)
    )
    assert replacement.s3_key != item.s3_key
    assert item.s3_key in manager.deleted
    assert replacement.file_name == "report.xlsx"
    assert use_case.download(item.id)[0] == office_file("xlsx")
    use_case.delete(item.id)
    assert repository.items == {} and manager.objects == {}


def test_default_conflict_and_per_type_default(setup):
    repository, manager, use_case = setup
    default = create(use_case, is_default=True)
    with pytest.raises(TemplateConflictError):
        create(use_case, is_default=True)
    other_type = create(use_case, template_type=TemplateTypes.PAYROLL, is_default=True)
    candidate = create(use_case)
    with pytest.raises(TemplateConflictError):
        use_case.update(
            candidate.id, {"is_default": True}, (office_file(), "new.docx", None)
        )
    assert repository.get(candidate.id) == candidate
    assert len(manager.objects) == 3
    assert default.s3_key in manager.objects and other_type.s3_key in manager.objects
    use_case.update(default.id, {"is_default": False})
    assert use_case.update(candidate.id, {"is_default": True}).is_default


@pytest.mark.parametrize("operation", ["create", "update"])
def test_database_failure_compensates_only_new_file(setup, operation):
    repository, manager, use_case = setup
    original = create(use_case)
    repository.fail = True
    with pytest.raises(RuntimeError, match="database failed"):
        if operation == "create":
            create(use_case)
        else:
            use_case.update(original.id, {}, (office_file(), "new.docx", None))
    assert list(manager.objects) == [original.s3_key]
    assert repository.get(original.id) == original


def test_s3_upload_failure_preserves_original(setup):
    repository, manager, use_case = setup
    original = create(use_case)
    manager.fail_upload = True
    with pytest.raises(TemplateStorageError):
        use_case.update(original.id, {"name": "new"}, (office_file(), "new.docx", None))
    assert repository.get(original.id) == original
    assert original.s3_key in manager.objects


def test_cleanup_failure_logged_after_commit(setup, caplog, monkeypatch):
    monkeypatch.setattr(
        "app.use_cases.templates.manage_templates.logger.propagate", True
    )
    repository, manager, use_case = setup
    original = create(use_case)
    manager.fail_delete = True
    use_case.delete(original.id)
    assert repository.items == {}
    assert original.s3_key in caplog.text


@pytest.mark.parametrize("operation", ["get", "delete", "download", "update"])
def test_missing_template(setup, operation):
    _, manager, use_case = setup
    with pytest.raises(TemplateNotFoundError):
        if operation == "update":
            use_case.update(uuid4(), {"name": "new"}, (office_file(), "new.docx", None))
        else:
            getattr(use_case, operation)(uuid4())
    assert manager.objects == {}


@pytest.mark.parametrize(
    "filename,content,mime",
    [
        ("x.pdf", b"%PDF-1.7", None),
        ("x.docx", b"", None),
        ("x.docx", b"fake", None),
        ("../x.docx", office_file(), None),
        ("x.docx", office_file("xlsx"), None),
        ("x.xlsx", office_file(), None),
        ("x.docx", office_file(), "application/pdf"),
    ],
)
def test_file_validation_rejects_before_s3(setup, filename, content, mime):
    _, manager, use_case = setup
    with pytest.raises(FileValidationError):
        use_case.create(TemplateTypes.WORK_TYPES, "Test", {}, content, filename, mime)
    assert manager.objects == {}


def test_size_limit_and_unique_replacement_keys(setup, monkeypatch):
    _, manager, use_case = setup
    item = create(use_case)
    updated = use_case.update(item.id, {}, (office_file(), "Шаблон.docx", None))
    assert item.s3_key != updated.s3_key
    monkeypatch.setattr("app.s3.s3_manager.MAX_FILE_SIZE_BYTES", 10)
    with pytest.raises(FileValidationError, match="100 MiB"):
        create(use_case)
    assert len(manager.objects) == 1


@pytest.fixture
def web(setup, monkeypatch):
    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY="test-secret-key-with-at-least-32-bytes",
        JWT_TOKEN_LOCATION=["headers"],
        RESTX_INCLUDE_ALL_MODELS=True,
    )
    JWTManager(app)
    api = Api(app)
    api.add_namespace(routes.template_files_ns)
    api.add_namespace(template_ns)
    monkeypatch.setattr(routes, "_use_case", lambda: setup[2])
    return app, app.test_client()


def headers(app, role="admin"):
    with app.app_context():
        token = create_access_token(
            identity=json.dumps({"user_id": str(uuid4()), "role": role})
        )
    return {"Authorization": f"Bearer {token}"}


def upload(client, auth, **metadata):
    return client.post(
        "/templates/add",
        headers=auth,
        data={
            "name": "Шаблон",
            "template_type": TemplateTypes.WORK_TYPES.value,
            **metadata,
            "file": (BytesIO(office_file()), "Шаблон.docx"),
        },
    )


@pytest.mark.parametrize("role", ["admin", "manager"])
def test_web_full_crud(web, role):
    app, client = web
    auth = headers(app, role)
    response = upload(client, auth, description="desc", is_default=True)
    assert response.status_code == 201, response.json
    item = response.json
    template_id = item["id"]
    assert client.get(f"/templates/{template_id}/view", headers=auth).json == item
    assert client.get("/templates/all", headers=auth).json["templates"] == [item]
    assert client.get("/templates/all?offset=1", headers=auth).json["templates"] == []
    assert (
        client.get(
            "/templates/all",
            query_string={"template_type": TemplateTypes.PAYROLL.value},
            headers=auth,
        ).json["templates"]
        == []
    )
    response = client.patch(
        f"/templates/{template_id}/edit",
        headers=auth,
        json={"description": None, "is_default": False, "is_pdf": True},
    )
    assert response.status_code == 200
    assert response.json["description"] is None and response.json["is_default"] is False
    response = client.patch(
        f"/templates/{template_id}/edit",
        headers=auth,
        data={"file": (BytesIO(office_file("xlsx")), "новый.xlsx")},
    )
    assert response.status_code == 200 and response.json["file_name"] == "новый.xlsx"
    response = client.get(f"/templates/{template_id}/download", headers=auth)
    assert response.data == office_file("xlsx")
    assert "attachment" in response.headers["Content-Disposition"]
    assert "filename*=UTF-8" in response.headers["Content-Disposition"]
    assert (
        client.delete(f"/templates/{template_id}/delete/hard", headers=auth).status_code
        == 200
    )
    assert client.get(f"/templates/{template_id}/view", headers=auth).status_code == 404


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/templates/add"),
        ("get", "/templates/all"),
        ("get", "/templates/types/all"),
        ("get", "/templates/{id}/view"),
        ("patch", "/templates/{id}/edit"),
        ("delete", "/templates/{id}/delete/hard"),
        ("get", "/templates/{id}/download"),
    ],
)
@pytest.mark.parametrize("role", [None, "user", "project-leader", "other"])
def test_web_access(web, method, path, role):
    app, client = web
    response = getattr(client, method)(
        path.format(id=uuid4()), headers=headers(app, role) if role else {}
    )
    assert response.status_code == (401 if role is None else 403)


@pytest.mark.parametrize(
    "data",
    [
        {"template_type": TemplateTypes.PAYROLL.value},
        {"name": None},
        {"name": ""},
        {"name": "x" * 256},
        {"is_default": None},
        {"is_pdf": "wrong"},
        {"s3_key": "other"},
        {},
        {"id": str(uuid4())},
    ],
)
def test_web_patch_validation(web, setup, data):
    app, client = web
    item = create(setup[2])
    response = client.patch(
        f"/templates/{item.id}/edit", headers=headers(app), json=data
    )
    assert response.status_code == 400
    assert setup[0].get(item.id) == item


@pytest.mark.parametrize(
    "query",
    [{"limit": 0}, {"limit": 1001}, {"offset": -1}, {"template_type": "invalid"}],
)
def test_web_filter_validation(web, query):
    app, client = web
    assert (
        client.get(
            "/templates/all", query_string=query, headers=headers(app)
        ).status_code
        == 400
    )


def test_web_conflict_upload_error_and_request_limits(web, setup, monkeypatch):
    app, client = web
    auth = headers(app)
    assert upload(client, auth, is_default=True).status_code == 201
    assert upload(client, auth, is_default=True).status_code == 409
    assert upload(client, auth, template_type="invalid").status_code == 400
    assert (
        client.post("/templates/add", headers=auth, data={"data": "{}"}).status_code
        == 400
    )
    assert (
        client.post(
            "/templates/add",
            headers=auth,
            data={"data": "invalid", "file": (BytesIO(office_file()), "x.docx")},
        ).status_code
        == 400
    )
    setup[1].fail_upload = True
    assert upload(client, auth).status_code == 503
    setup[1].fail_upload = False
    monkeypatch.setattr(routes, "MAX_FILE_SIZE_BYTES", 10)
    assert upload(client, auth).status_code == 413


def test_swagger_and_model_contract(web):
    _, client = web
    schema = client.get("/swagger.json").json
    assert "/templates/generate" in schema["paths"]
    assert "/templates/generate-new" in schema["paths"]
    assert "/templates/{template_id}/download" in schema["paths"]
    assert schema["definitions"]["StoredTemplateCreate"]["required"] == [
        "name",
        "template_type",
    ]
    assert (
        "template_type" not in schema["definitions"]["StoredTemplateEdit"]["properties"]
    )
    assert schema["paths"]["/templates/add"]["post"]["consumes"] == [
        "multipart/form-data"
    ]
    parameters = {
        row["name"]: row
        for row in schema["paths"]["/templates/add"]["post"]["parameters"]
        if row["in"] == "formData"
    }
    assert set(parameters) == {
        "file", "name", "template_type", "description", "output_file_name",
        "is_horizontal", "is_pdf", "is_default",
    }
    assert all(parameters[name]["required"] for name in ("file", "name", "template_type"))
    assert parameters["template_type"]["enum"] == [value.value for value in TemplateTypes]
    for name in ("is_horizontal", "is_pdf", "is_default"):
        assert parameters[name]["type"] == "boolean"
        assert parameters[name]["default"] is False
    indexes = {index.name: index for index in Templates.__table__.indexes}
    ddl = str(
        CreateIndex(indexes[DEFAULT_TEMPLATE_INDEX]).compile(
            dialect=postgresql.dialect()
        )
    )
    assert "UNIQUE" in ddl and "WHERE is_default" in ddl
    assert "ix_templates_template_type" in indexes
    assert Templates.__table__.c.template_type.type.enums == [
        v.value for v in TemplateTypes
    ]


def test_upload_separate_fields_and_boolean_values(web):
    app, client = web
    response = upload(
        client, headers(app), description="Описание", output_file_name="Результат",
        is_horizontal="true", is_pdf="false", is_default="true",
    )
    assert response.status_code == 201, response.json
    item = response.get_json()
    assert item["description"] == "Описание"
    assert item["output_file_name"] == "Результат"
    assert item["is_horizontal"] is True
    assert item["is_pdf"] is False
    assert item["is_default"] is True


@pytest.mark.parametrize("value", ["", "   ", "\t\r\n"])
def test_upload_blank_optional_text_is_stored_as_null(web, setup, value):
    app, client = web
    response = upload(
        client, headers(app), description=value, output_file_name=value,
        is_horizontal="true", is_pdf="false",
    )
    assert response.status_code == 201, response.json
    item = response.get_json()
    assert item["description"] is None
    assert item["output_file_name"] is None
    stored = setup[2].list(None, 0, 100)[0]
    assert stored.description is None
    assert stored.output_file_name is None
    assert stored.is_horizontal is True
    assert stored.is_pdf is False


def test_upload_nonblank_optional_text_keeps_surrounding_whitespace(web):
    app, client = web
    response = upload(
        client, headers(app), description="  Описание  ", output_file_name=" Отчёт ",
    )
    assert response.status_code == 201, response.json
    item = response.get_json()
    assert item["description"] == "  Описание  "
    assert item["output_file_name"] == " Отчёт "


@pytest.mark.parametrize("field", ["name", "template_type", "is_horizontal", "is_pdf", "is_default"])
def test_upload_empty_required_and_boolean_fields_are_invalid(web, field):
    app, client = web
    response = upload(client, headers(app), **{field: ""})
    assert response.status_code == 400, response.json
    assert field in response.get_json()["errors"]


@pytest.mark.parametrize(
    "invalid", ["missing_name", "missing_type", "boolean", "unknown", "duplicate", "mixed"]
)
def test_upload_form_validation_preserves_storage(web, setup, invalid):
    app, client = web
    data: MultiDict[str, Any] = MultiDict({"name": "Шаблон", "template_type": "work_types"})
    if invalid == "missing_name":
        data.pop("name")
    elif invalid == "missing_type":
        data.pop("template_type")
    elif invalid == "boolean":
        data["is_pdf"] = "invalid"
    elif invalid == "unknown":
        data["s3_key"] = "injected"
    elif invalid == "duplicate":
        data.add("name", "Другое название")
    else:
        data["data"] = '{}'
    data["file"] = (BytesIO(office_file()), "Шаблон.docx")
    before = dict(setup[1].objects)
    response = client.post("/templates/add", headers=headers(app), data=data)
    assert response.status_code == 400, response.json
    assert setup[1].objects == before


def test_legacy_upload_metadata_remains_supported(web):
    app, client = web
    response = client.post(
        "/templates/add", headers=headers(app),
        data={
            "data": json.dumps({"name": "Legacy", "template_type": "work_types"}),
            "file": (BytesIO(office_file()), "legacy.docx"),
        },
    )
    assert response.status_code == 201, response.json
    assert response.get_json()["name"] == "Legacy"


def test_only_default_index_integrity_error_maps_to_conflict():
    error = IntegrityError("insert", {}, Exception(DEFAULT_TEMPLATE_INDEX))
    with pytest.raises(TemplateConflictError):
        SQLAlchemyTemplateRepository._map_integrity(error)
    other = IntegrityError("insert", {}, Exception("other constraint"))
    with pytest.raises(IntegrityError) as caught:
        SQLAlchemyTemplateRepository._map_integrity(other)
    assert caught.value is other


def test_migration_matches_model():
    path = Path(__file__).parents[1] / "alembic/versions/20261019120000_templates.py"
    spec = spec_from_file_location("templates_migration", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "20261016120000"
    assert list(module.TEMPLATE_TYPES) == [v.label() for v in TemplateTypes]


def test_type_codes_migration_matches_enum():
    path = (
        Path(__file__).parents[1]
        / "alembic/versions/20261019130000_template_type_codes.py"
    )
    spec = spec_from_file_location("template_type_codes_migration", path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.down_revision == "20261019120000"
    assert list(module.TYPE_CODES) == [
        (value.label(), value.value) for value in TemplateTypes
    ]


@pytest.mark.parametrize("role", ["admin", "manager"])
def test_type_catalog_and_response_labels(web, role):
    app, client = web
    auth = headers(app, role)
    response = client.get("/templates/types/all", headers=auth)
    assert response.status_code == 200
    assert response.json == {
        "template_types": [
            {"value": value.value, "label": value.label()} for value in TemplateTypes
        ]
    }
    assert len({item["value"] for item in response.json["template_types"]}) == 5
    for value in TemplateTypes:
        created = upload(client, auth, template_type=value.value)
        assert created.status_code == 201
        item = created.json
        assert item["template_type"] == value.value
        assert item["template_type_label"] == value.label()
        assert client.get(f"/templates/{item['id']}/view", headers=auth).json == item
        listed = client.get(
            "/templates/all", query_string={"template_type": value.value}, headers=auth
        )
        assert listed.json["templates"] == [item]
    assert upload(client, auth, template_type="Виды работ").status_code == 400
    assert (
        client.get(
            "/templates/all", query_string={"template_type": "Виды работ"}, headers=auth
        ).status_code
        == 400
    )
    swagger = client.get("/swagger.json").json
    assert "/templates/types/all" in swagger["paths"]
    assert (
        swagger["definitions"]["StoredTemplate"]["properties"]["template_type_label"][
            "type"
        ]
        == "string"
    )
    assert swagger["definitions"]["StoredTemplateCreate"]["properties"][
        "template_type"
    ]["enum"] == [value.value for value in TemplateTypes]


@pytest.mark.parametrize(
    "filename,content",
    [
        ("file.pdf", b"%PDF-1.7"),
        ("file.docx", b""),
        ("file.docx", b"invalid Office ZIP"),
        ("x" * 251 + ".docx", office_file()),
    ],
)
@pytest.mark.parametrize("operation", ["create", "replace"])
def test_invalid_files_return_http_400(web, setup, filename, content, operation):
    app, client = web
    auth = headers(app)
    original = create(setup[2])
    before = dict(setup[1].objects)
    if operation == "create":
        response = client.post(
            "/templates/add",
            headers=auth,
            data={
                "data": json.dumps(
                    {"name": "Test", "template_type": TemplateTypes.WORK_TYPES.value}
                ),
                "file": (BytesIO(content), filename),
            },
        )
    else:
        response = client.patch(
            f"/templates/{original.id}/edit",
            headers=auth,
            data={
                "file": (BytesIO(content), filename),
            },
        )
    assert issubclass(FileValidationError, ValueError)
    assert response.status_code == 400, response.json
    assert setup[1].objects == before
    assert setup[0].get(original.id) == original


def test_office_fixture_has_fixed_zip_timestamps():
    for extension in ("docx", "xlsx"):
        with ZipFile(BytesIO(office_file(extension))) as archive:
            assert all(
                info.date_time == (2020, 1, 1, 0, 0, 0) for info in archive.infolist()
            )
