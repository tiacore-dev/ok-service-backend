import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from flask_restx import Api, Model, fields, marshal

from app.adapters.projects import SQLAlchemyProjectRepository
from app.routes.models.place_models import place_model
from app.web.fields import NestedMap
from app.web.projects import routes
from app.web.projects.models import project_stats_model


@pytest.fixture
def projects_web(monkeypatch):
    app = Flask(__name__)
    app.config.update(
        TESTING=True, JWT_SECRET_KEY="test-secret-key-with-at-least-32-bytes"
    )
    JWTManager(app)
    api = Api(app)
    api.add_namespace(routes.project_ns)
    api.models[place_model.name] = place_model
    repository = Mock(spec=SQLAlchemyProjectRepository)
    monkeypatch.setattr(routes, "_repository", lambda: repository)
    return app, app.test_client(), repository


def headers(app, role="manager"):
    with app.app_context():
        token = create_access_token(
            identity=json.dumps({"user_id": str(uuid4()), "role": role})
        )
    return {"Authorization": f"Bearer {token}"}


def payload():
    return {
        "stats": {
            str(uuid4()): {
                "project_work_quantity": value,
                "project_work_summ": value * 100,
                "shift_report_details_quantity": 0,
                "shift_report_details_summ": None,
                "shift_report_details_summ_by_estimate": value * 50,
                "presented_quantity": None,
                "presented_summ": None,
                "accepted_quantity": 0,
                "accepted_summ": 0,
                "project_work_name": "Работа" if value else None,
            }
            for value in (1.5, 0)
        },
        "material_stats": {
            str(uuid4()): {
                "project_material_quantity": value,
                "project_material_summ": value * 100,
                "shift_report_material_quantity": 0,
                "shift_report_material_summ_by_estimate": 0,
                "material_name": "Материал" if value else None,
            }
            for value in (2.5, 0)
        },
    }


@pytest.mark.parametrize("role", ["admin", "manager", "project-leader"])
def test_http_response_preserves_ids_values_nulls_and_zeros(projects_web, role):
    app, client, repository = projects_web
    expected = payload()
    repository.get_project_stats.return_value = expected["stats"]
    repository.get_project_material_stats.return_value = expected["material_stats"]
    project_id = uuid4()

    for _ in range(2):
        response = client.get(
            f"/projects/{project_id}/get-stat", headers=headers(app, role)
        )
        assert response.status_code == 200
        assert response.json == {"msg": "Project stats fetched successfully", **expected}
    repository.get_project_stats.assert_called_with(project_id)
    repository.get_project_material_stats.assert_called_with(project_id)


@pytest.mark.parametrize(
    "empty_fields", [("stats",), ("material_stats",), ("stats", "material_stats")]
)
def test_empty_dictionaries_remain_empty(projects_web, empty_fields):
    app, client, repository = projects_web
    expected = payload()
    for field in empty_fields:
        expected[field] = {}
    repository.get_project_stats.return_value = expected["stats"]
    repository.get_project_material_stats.return_value = expected["material_stats"]

    response = client.get(f"/projects/{uuid4()}/get-stat", headers=headers(app))

    assert response.status_code == 200
    assert response.json == {"msg": "Project stats fetched successfully", **expected}


@pytest.mark.parametrize("role,status", [(None, 401), ("user", 403)])
def test_unauthorized_requests_do_not_read_stats(projects_web, role, status):
    app, client, repository = projects_web
    response = client.get(
        f"/projects/{uuid4()}/get-stat", headers=headers(app, role) if role else {}
    )
    assert response.status_code == status
    repository.get_project_stats.assert_not_called()
    repository.get_project_material_stats.assert_not_called()


def test_invalid_project_id_is_rejected_before_reading_stats(projects_web):
    app, client, repository = projects_web
    response = client.get("/projects/bad/get-stat", headers=headers(app))
    assert response.status_code == 400
    repository.get_project_stats.assert_not_called()
    repository.get_project_material_stats.assert_not_called()


def test_swagger_describes_id_maps(projects_web):
    _, client, _ = projects_web
    response = client.get("/swagger.json")
    assert response.status_code == 200
    definitions = response.json["definitions"]
    properties = definitions["ProjectStatsResponse"]["properties"]
    for field, model in (
        ("stats", "ProjectStats"), ("material_stats", "ProjectMaterialStats"),
    ):
        schema = properties[field]
        assert schema["type"] == "object"
        assert schema["additionalProperties"] == {"$ref": f"#/definitions/{model}"}
        assert "properties" not in schema
        assert model in definitions


def test_concurrent_http_responses_keep_their_own_ids(projects_web, monkeypatch):
    app, _, repository = projects_web
    expected = {uuid4(): payload(), uuid4(): payload()}
    repository.get_project_stats.side_effect = (
        lambda project_id: expected[project_id]["stats"]
    )
    repository.get_project_material_stats.side_effect = (
        lambda project_id: expected[project_id]["material_stats"]
    )
    rendezvous = Barrier(2)
    thread_state = local()
    quantity_field = project_stats_model.resolved["project_work_quantity"]
    original_format = quantity_field.format

    def synchronized_format(value):
        visits = getattr(thread_state, "visits", 0)
        if visits < 2:
            thread_state.visits = visits + 1
            rendezvous.wait(timeout=5)
        return original_format(value)

    monkeypatch.setattr(quantity_field, "format", synchronized_format)
    auth = headers(app)

    def request_stats(project_id: UUID):
        with app.test_client() as client:
            response = client.get(f"/projects/{project_id}/get-stat", headers=auth)
            assert response.status_code == 200
            return response.json

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(request_stats, expected))
    for project_id, response in zip(expected, responses):
        assert response == {
            "msg": "Project stats fetched successfully", **expected[project_id]
        }


@pytest.mark.parametrize("model", [None, {}])
def test_map_schema_requires_a_named_model(model):
    with pytest.raises(fields.MarshallingError, match="require a named Model"):
        NestedMap(model).schema()


def test_map_rejects_non_dictionary():
    field = NestedMap(Model("Item", {"value": fields.Float}))
    with pytest.raises(fields.MarshallingError, match="must be a dictionary"):
        marshal({"stats": []}, {"stats": field})


def test_map_uses_attribute_and_normalizes_missing_value():
    field = NestedMap(Model("Item", {"value": fields.Float}), attribute="source")
    assert marshal({"source": {"id": {"value": 2}}}, {"stats": field}) == {
        "stats": {"id": {"value": 2.0}}
    }
    assert marshal({}, {"stats": field}) == {"stats": {}}
