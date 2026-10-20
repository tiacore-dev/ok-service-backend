from io import BytesIO
from typing import Any
from uuid import uuid4

import pytest

from app.adapters.templates.s3_storage import S3TemplateStorage
from app.database.models import ApiKeys, KeyPermissionTypeRelations, PermissionTypes
from app.database.time_utils import utc_epoch_milliseconds
from app.use_cases.templates.manage_templates import TemplateUseCase
from app.utils.api_key_permissions import set_api_key_permissions
from app.web.template_generation import routes as generation_routes
from app.web.templates import routes
from tests.test_stored_templates import (
    FakeRepository,
    FakeS3Manager,
    create,
    office_file,
)

OPERATIONS = [
    ("POST", "/templates/add", 201),
    ("GET", "/templates/all", 200),
    ("GET", "/templates/types/all", 200),
    ("GET", "/templates/params", 200),
    ("GET", "/templates/{template_id}/view", 200),
    ("PATCH", "/templates/{template_id}/edit", 200),
    ("DELETE", "/templates/{template_id}/delete/hard", 200),
    ("GET", "/templates/{template_id}/download", 200),
    ("POST", "/templates/generate", 200),
]


@pytest.fixture
def template_key_context(db_session, monkeypatch):
    # The shared clean_db fixture removes permission types after every test.
    set_api_key_permissions()
    use_case = TemplateUseCase(FakeRepository(), S3TemplateStorage(FakeS3Manager()))
    item = create(use_case)
    monkeypatch.setattr(routes, "_use_case", lambda: use_case)

    from app.use_cases.template_generation import GenerateTemplateUseCase
    from app.use_cases.template_generation.dto import GeneratedDocument

    class Dependencies:
        def get(self, template_id):
            return use_case.get(template_id)

        def get_default(self, template_type):
            return item

        def execute(self, kind, parameters):
            return {"works": []}

        def presigned_url(self, key):
            return "https://example.test/template.docx"

        def generate(self, command):
            return GeneratedDocument(
                [b"generated"], command.content_type, command.filename, lambda: None
            )

    dependency = Dependencies()
    generation = GenerateTemplateUseCase(dependency, dependency, dependency, dependency)
    monkeypatch.setattr(generation_routes, "_use_case", lambda: generation)
    key = ApiKeys(
        api_key_id=uuid4(), name=f"template-key-{uuid4()}", token=str(uuid4())
    )
    db_session.add(key)
    db_session.commit()
    return item.id, key


def call(client, method, route, identifier, token):
    kwargs: dict[str, Any] = {"headers": {"API-Key": token}}
    if route == "/templates/add":
        kwargs["data"] = {
            "name": "Test",
            "template_type": "work_types",
            "file": (BytesIO(office_file()), "test.docx"),
        }
    elif method == "PATCH":
        kwargs["json"] = {"name": "Changed"}
    elif route == "/templates/params":
        kwargs["query_string"] = {"template_type": "payroll"}
    elif route == "/templates/generate":
        kwargs["json"] = {"template_type": "work_types", "template_id": str(identifier)}
    return client.open(route.format(template_id=identifier), method=method, **kwargs)


@pytest.mark.parametrize("method,route,status", OPERATIONS)
@pytest.mark.parametrize("grant", [False, True])
def test_each_template_route_requires_its_own_api_key_permission(
    client, db_session, template_key_context, method, route, status, grant
):
    identifier, key = template_key_context
    permission = (
        db_session.query(PermissionTypes)
        .filter_by(description=f"{method} {route}")
        .one()
    )
    if grant:
        db_session.add(
            KeyPermissionTypeRelations(
                api_key_id=key.api_key_id,
                permission_type_id=permission.permission_type_id,
            )
        )
        db_session.commit()
    response = call(client, method, route, identifier, key.token)
    assert response.status_code == (status if grant else 403), (
        response.json if response.is_json else response.data
    )


@pytest.mark.parametrize("key_state", ["expired", "invalid", "wrong_permission"])
def test_params_rejects_unusable_or_unrelated_keys(
    client, db_session, template_key_context, key_state
):
    identifier, key = template_key_context
    permission = (
        db_session.query(PermissionTypes)
        .filter_by(
            code="templates-list"
            if key_state == "wrong_permission"
            else "templates-params"
        )
        .one()
    )
    db_session.add(
        KeyPermissionTypeRelations(
            api_key_id=key.api_key_id, permission_type_id=permission.permission_type_id
        )
    )
    if key_state == "expired":
        key.expires_at = utc_epoch_milliseconds() - 1
    db_session.commit()
    response = call(
        client,
        "GET",
        "/templates/params",
        identifier,
        "invalid" if key_state == "invalid" else key.token,
    )
    assert response.status_code == 403
