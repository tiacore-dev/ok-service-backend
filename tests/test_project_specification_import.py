import json
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4
from uuid import UUID

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from flask_restx import Api, Namespace

from app.use_cases.project_specification_import import (
    ImportProjectSpecificationUseCase,
    ProjectMaterialImportItem,
    ProjectSpecificationImportActor,
    ProjectSpecificationImportCommand,
    ProjectSpecificationImportError,
    ProjectWorkImportItem,
)
from app.domain.project_materials import ProjectMaterial
from app.domain.project_works import ProjectWork
from app.web.projects import routes
from app.web.projects.routes import (
    ProjectSpecificationImport,
    project_specification_import_material_model,
    project_specification_import_model,
    project_specification_import_request_model,
    project_specification_import_work_model,
)

ImportCall = tuple[
    UUID,
    ProjectSpecificationImportActor,
    list[ProjectWork],
    list[ProjectMaterial],
]


class _Repository:
    def __init__(self, projects: list[UUID]):
        self.projects = projects
        self.called: ImportCall | None = None

    def get_project_ids_by_leader(self, user_id: UUID) -> list[UUID]:
        return self.projects

    def import_specification(
        self,
        project_id: UUID,
        actor: ProjectSpecificationImportActor,
        works: list[ProjectWork],
        materials: list[ProjectMaterial],
    ) -> None:
        self.called = (project_id, actor, works, materials)


@pytest.fixture
def import_web(monkeypatch):
    app = Flask(__name__)
    app.config.update(
        TESTING=True, JWT_SECRET_KEY="test-secret-key-with-at-least-32-bytes"
    )
    JWTManager(app)
    Api(app).add_namespace(routes.project_ns)
    app.extensions["redis"] = Mock()
    repository = Mock(spec=_Repository([]))
    repository.get_project_ids_by_leader.return_value = []
    monkeypatch.setattr(
        routes, "SQLAlchemyProjectSpecificationImportRepository",
        lambda **kwargs: repository,
    )
    return app, app.test_client(), repository


def _import_headers(app, role="manager"):
    with app.app_context():
        token = create_access_token(
            identity=json.dumps({"user_id": str(uuid4()), "role": role})
        )
    return {"Authorization": f"Bearer {token}"}


def _import_payload(
    work_quantity: int | float = 1, material_quantity: int | float = 1
):
    project_work_id = str(uuid4())
    return {
        "project_works": [{
            "project_work_id": project_work_id,
            "project_work_name": "Work",
            "work": str(uuid4()),
            "quantity": work_quantity,
        }],
        "project_materials": [{
            "project_material_id": str(uuid4()),
            "material": str(uuid4()),
            "quantity": material_quantity,
            "project_work": project_work_id,
        }],
    }


@pytest.mark.parametrize(
    "work_quantity,material_quantity,message",
    [
        (-1, 1, "Project work quantity must be non-negative."),
        (1, 0, "Project material quantity must be positive."),
        (1, -1, "Project material quantity must be positive."),
    ],
)
def test_import_returns_400_with_domain_validation_message(
    import_web, work_quantity, material_quantity, message,
):
    app, client, repository = import_web

    response = client.post(
        f"/projects/{uuid4()}/import-works-and-materials",
        json=_import_payload(work_quantity, material_quantity),
        headers=_import_headers(app),
    )

    assert response.status_code == 400
    assert response.get_json() == {"msg": message}
    repository.import_specification.assert_not_called()


@pytest.mark.parametrize("work_quantity", [0, 1])
def test_import_accepts_valid_quantities(import_web, work_quantity):
    app, client, repository = import_web

    response = client.post(
        f"/projects/{uuid4()}/import-works-and-materials",
        json=_import_payload(work_quantity, 0.01),
        headers=_import_headers(app),
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "project_works_created": 1, "project_materials_created": 1,
    }
    repository.import_specification.assert_called_once()


@pytest.mark.parametrize("role", ["user", "project-leader"])
def test_import_preserves_forbidden_access(import_web, role):
    app, client, repository = import_web

    response = client.post(
        f"/projects/{uuid4()}/import-works-and-materials",
        json=_import_payload(),
        headers=_import_headers(app, role),
    )

    assert response.status_code == 403
    repository.import_specification.assert_not_called()


def test_import_uses_path_project_and_calculates_sums():
    project_id, user_id, work_id, material_id, project_work_id = (uuid4() for _ in range(5))
    repository = _Repository([])
    command = ProjectSpecificationImportCommand(
        [ProjectWorkImportItem(project_work_id, "Work", work_id, Decimal("2"), Decimal("3"))],
        [
            ProjectMaterialImportItem(
                uuid4(),
                material_id,
                Decimal("4"),
                Decimal("5"),
                project_work_id,
                project_material_name="Concrete",
            )
        ],
    )

    ImportProjectSpecificationUseCase(repository).execute(
        project_id, command, ProjectSpecificationImportActor(user_id, "manager")
    )

    assert repository.called is not None
    _, _, works, materials = repository.called
    assert works[0].project == project_id
    assert works[0].summ == Decimal("6")
    assert materials[0].project_work == project_work_id
    assert materials[0].project_material_name == "Concrete"
    assert materials[0].summ == Decimal("20")


def test_import_rejects_material_reference_outside_payload():
    repository = _Repository([])
    command = ProjectSpecificationImportCommand(
        [],
        [ProjectMaterialImportItem(uuid4(), uuid4(), Decimal("1"), None, uuid4())],
    )

    with pytest.raises(ProjectSpecificationImportError, match="outside import"):
        ImportProjectSpecificationUseCase(repository).execute(
            uuid4(), command, ProjectSpecificationImportActor(uuid4(), "admin")
        )


def test_import_swagger_contract_describes_request_payload():
    app = Flask(__name__)
    api = Api(app)
    namespace = Namespace("project-specification-import")
    for model in (
        project_specification_import_model,
        project_specification_import_request_model,
        project_specification_import_work_model,
        project_specification_import_material_model,
    ):
        namespace.models[model.name] = model
    namespace.add_resource(
        ProjectSpecificationImport,
        "/projects/<string:project_id>/import-works-and-materials",
    )
    api.add_namespace(namespace)

    response = app.test_client().get("/swagger.json")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    operation = payload["paths"][
        "/project-specification-import/projects/{project_id}/import-works-and-materials"
    ]["post"]
    body_parameter = next(
        parameter
        for parameter in operation["parameters"]
        if parameter["in"] == "body"
    )
    assert body_parameter["schema"] == {
        "$ref": "#/definitions/ProjectSpecificationImportRequest"
    }

    definitions = payload["definitions"]
    request = definitions["ProjectSpecificationImportRequest"]
    assert request["required"] == ["project_materials", "project_works"]
    assert request["properties"]["project_works"]["items"] == {
        "$ref": "#/definitions/ProjectSpecificationImportWork"
    }
    assert request["properties"]["project_materials"]["items"] == {
        "$ref": "#/definitions/ProjectSpecificationImportMaterial"
    }
    assert definitions["ProjectSpecificationImportWork"]["required"] == [
        "project_work_id",
        "project_work_name",
        "quantity",
        "work",
    ]
    assert definitions["ProjectSpecificationImportMaterial"]["required"] == [
        "material",
        "project_material_id",
        "quantity",
    ]
    assert "project_material_name" in definitions["ProjectSpecificationImportMaterial"]["properties"]
