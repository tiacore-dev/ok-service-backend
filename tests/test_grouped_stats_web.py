import copy
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local
from unittest.mock import Mock
from uuid import uuid4

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from flask_restx import Api, marshal

from app.adapters.objects import SQLAlchemyObjectRepository
from app.adapters.projects import SQLAlchemyProjectRepository
from app.database.managers.projects_managers import ProjectsManager
from app.routes.models.place_models import place_model
from app.web.objects import routes as objects
from app.web.objects.models import (
    object_stats_details_response,
    object_stats_response,
    work_stats_summary_model,
)
from app.web.project_leaders import routes as leaders


WORK = {
    "project_work_quantity": 10.5,
    "project_work_summ": 1050,
    "shift_report_details_quantity": 0,
    "shift_report_details_summ": None,
    "shift_report_details_summ_by_estimate": 0,
    "presented_quantity": None,
    "presented_summ": None,
    "accepted_quantity": 0,
    "accepted_summ": 0,
}
MATERIAL = {
    "project_material_quantity": 20.5,
    "project_material_summ": 205,
    "shift_report_material_quantity": 0,
    "shift_report_material_summ_by_estimate": 0,
}


@pytest.fixture
def grouped_web(monkeypatch):
    app = Flask(__name__)
    app.config.update(
        TESTING=True, JWT_SECRET_KEY="test-secret-key-with-at-least-32-bytes"
    )
    JWTManager(app)
    api = Api(app)
    api.add_namespace(objects.object_ns)
    api.add_namespace(leaders.project_leader_ns)
    api.models[place_model.name] = place_model
    object_repository = Mock(spec=SQLAlchemyObjectRepository)
    leader_repository = Mock(spec=SQLAlchemyProjectRepository)
    monkeypatch.setattr(objects, "_repository", lambda: object_repository)
    monkeypatch.setattr(leaders, "_repository", lambda: leader_repository)
    actor_id = uuid4()

    def headers(role="manager"):
        with app.app_context():
            token = create_access_token(
                identity=json.dumps({"user_id": str(actor_id), "role": role})
            )
        return {"Authorization": f"Bearer {token}"}

    return (
        app, app.test_client(), object_repository, leader_repository, actor_id, headers
    )


def grouped_payload(detailed):
    work_id, material_id = str(uuid4()), str(uuid4())
    work = {**WORK, "project_work_name": "Работа"}
    material = {**MATERIAL, "material_name": "Материал"}
    work_stats = {work_id: work} if detailed else dict(WORK)
    return {
        "total": copy.deepcopy(work_stats),
        "material_totals": {material_id: material} if detailed else dict(MATERIAL),
        "projects": [
            {
                "project_id": str(uuid4()), "name": f"Проект {index}",
                "stats": copy.deepcopy(work_stats),
                "material_stats": {material_id: dict(material)},
            }
            for index in range(2)
        ],
    }


@pytest.mark.parametrize("kind", ["objects", "project-leaders"])
@pytest.mark.parametrize("detailed", [False, True])
@pytest.mark.parametrize("role", ["admin", "manager", "project-leader"])
def test_grouped_http_preserves_payload(grouped_web, kind, detailed, role):
    _, client, object_repo, leader_repo, actor_id, headers = grouped_web
    expected = grouped_payload(detailed)
    repo = object_repo if kind == "objects" else leader_repo
    prefix = "get_object_stats" if kind == "objects" else "get_project_leader_stats"
    method = getattr(repo, prefix + ("_details" if detailed else ""))
    method.return_value = expected
    suffix = "get-stat-details" if detailed else "get-stat"
    for _ in range(2):
        response = client.get(f"/{kind}/{actor_id}/{suffix}", headers=headers(role))
        assert response.status_code == 200
        assert response.json["stats"] == expected
    method.assert_called_with(actor_id)


@pytest.mark.parametrize("kind", ["objects", "project-leaders"])
@pytest.mark.parametrize("empty_projects", [False, True])
def test_empty_detailed_maps(grouped_web, kind, empty_projects):
    _, client, object_repo, leader_repo, actor_id, headers = grouped_web
    expected = {"total": {}, "material_totals": {}, "projects": []}
    if not empty_projects:
        expected["projects"] = [{
            "project_id": str(uuid4()), "name": "Пустой проект",
            "stats": {}, "material_stats": {},
        }]
    repo = object_repo if kind == "objects" else leader_repo
    method = (
        repo.get_object_stats_details
        if kind == "objects" else repo.get_project_leader_stats_details
    )
    method.return_value = expected
    response = client.get(f"/{kind}/{actor_id}/get-stat-details", headers=headers())
    assert response.status_code == 200
    assert response.json["stats"] == expected


@pytest.mark.parametrize("kind", ["objects", "project-leaders"])
def test_summary_without_projects_keeps_empty_total(grouped_web, kind):
    _, client, object_repo, leader_repo, actor_id, headers = grouped_web
    expected = {
        "total": {}, "material_totals": dict.fromkeys(MATERIAL, 0), "projects": [],
    }
    repo = object_repo if kind == "objects" else leader_repo
    method = (
        repo.get_object_stats
        if kind == "objects" else repo.get_project_leader_stats
    )
    method.return_value = expected
    response = client.get(f"/{kind}/{actor_id}/get-stat", headers=headers())
    assert response.status_code == 200
    assert response.json["stats"] == expected


def test_objects_collection_stays_flat_and_preserves_totals(grouped_web):
    _, client, repo, _, _, headers = grouped_web
    expected = {
        "total": dict(WORK), "material_totals": dict(MATERIAL), "total_count": 3,
        "objects": [{
            "object_id": str(uuid4()), "name": "Объект", "stats": dict(WORK),
            "material_totals": dict(MATERIAL),
        }],
    }
    repo.get_all_objects_stats.return_value = expected
    response = client.get(
        "/objects/get-stat?offset=1&limit=1&search=test", headers=headers()
    )
    assert response.status_code == 200
    assert response.json["stats"] == expected
    query = repo.get_all_objects_stats.call_args.args[0]
    assert (query.offset, query.limit, query.search) == (1, 1, "test")


def test_swagger_distinguishes_summary_and_detailed_maps(grouped_web):
    _, client, _, _, _, _ = grouped_web
    response = client.get("/swagger.json")
    assert response.status_code == 200
    definitions = response.json["definitions"]
    for model, field, item in (
        ("ObjectProjectStats", "material_stats", "MaterialStatsItem"),
        ("ObjectProjectStatsDetails", "stats", "WorkStatsItem"),
        ("ObjectProjectStatsDetails", "material_stats", "MaterialStatsItem"),
        ("ObjectStatsDetailsPayload", "total", "WorkStatsItem"),
        ("ObjectStatsDetailsPayload", "material_totals", "MaterialStatsItem"),
    ):
        assert definitions[model]["properties"][field] == {
            "type": "object", "additionalProperties": {"$ref": f"#/definitions/{item}"},
        }
    assert definitions["ObjectProjectStats"]["properties"]["stats"] == {
        "$ref": "#/definitions/WorkStatsSummary"
    }
    assert definitions["ObjectStatsPayload"]["properties"]["projects"]["items"] == {
        "$ref": "#/definitions/ObjectProjectStats"
    }
    details = definitions["ObjectStatsDetailsPayload"]["properties"]
    assert details["projects"]["items"] == {
        "$ref": "#/definitions/ObjectProjectStatsDetails"
    }


@pytest.mark.parametrize("kind", ["objects", "project-leaders"])
@pytest.mark.parametrize("detailed", [False, True])
@pytest.mark.parametrize("role,status", [(None, 401), ("user", 403)])
def test_grouped_access_remains_restricted(grouped_web, kind, detailed, role, status):
    _, client, object_repo, leader_repo, actor_id, headers = grouped_web
    suffix = "get-stat-details" if detailed else "get-stat"
    response = client.get(
        f"/{kind}/{actor_id}/{suffix}", headers=headers(role) if role else {},
    )
    assert response.status_code == status
    object_repo.get_object_stats.assert_not_called()
    object_repo.get_object_stats_details.assert_not_called()
    leader_repo.get_project_leader_stats.assert_not_called()
    leader_repo.get_project_leader_stats_details.assert_not_called()


@pytest.mark.parametrize("kind", ["objects", "project-leaders"])
@pytest.mark.parametrize("detailed", [False, True])
def test_invalid_group_id_does_not_read_stats(grouped_web, kind, detailed):
    _, client, object_repo, leader_repo, _, headers = grouped_web
    suffix = "get-stat-details" if detailed else "get-stat"
    response = client.get(f"/{kind}/bad/{suffix}", headers=headers())
    assert response.status_code == 400
    object_repo.get_object_stats.assert_not_called()
    object_repo.get_object_stats_details.assert_not_called()
    leader_repo.get_project_leader_stats.assert_not_called()
    leader_repo.get_project_leader_stats_details.assert_not_called()


@pytest.mark.parametrize("kind", ["objects", "project-leaders"])
@pytest.mark.parametrize("detailed", [False, True])
def test_real_aggregation_survives_serialization(monkeypatch, kind, detailed):
    manager = ProjectsManager()
    project_ids = [uuid4(), uuid4()]
    work_id, material_id = str(uuid4()), str(uuid4())
    work = {**WORK, "project_work_name": "Работа"}
    material = {**MATERIAL, "material_name": "Материал"}
    by_project = {project_id: {work_id: dict(work)} for project_id in project_ids}
    monkeypatch.setattr(manager, "get_project_stats_many", lambda ids: by_project)
    projects = [
        (project_id, f"Проект {index}")
        for index, project_id in enumerate(project_ids)
    ]

    def grouped_stats(group_id):
        return manager._build_grouped_project_stats(projects, detailed=detailed)

    material_statistics = Mock()
    material_statistics.get_project_material_stats.side_effect = (
        lambda project_id: {material_id: dict(material)}
    )
    if kind == "objects":
        method = "get_object_stats_details" if detailed else "get_object_stats"
        monkeypatch.setattr(manager, method, grouped_stats)
        repository = SQLAlchemyObjectRepository(
            projects_manager=manager, material_statistics=material_statistics,
        )
    else:
        method = (
            "get_project_leader_stats_details"
            if detailed else "get_project_leader_stats"
        )
        monkeypatch.setattr(manager, method, grouped_stats)
        repository = SQLAlchemyProjectRepository(
            manager=manager, material_statistics=material_statistics,
        )
    payload = getattr(repository, method)(uuid4())
    model = object_stats_details_response if detailed else object_stats_response
    result = marshal({"msg": "ok", "stats": payload}, model)
    assert result == {"msg": "ok", "stats": payload}
    assert isinstance(result, dict)
    stats = result["stats"]
    assert isinstance(stats, dict)
    doubled_work = {
        field: value * 2 if isinstance(value, (int, float)) else value
        for field, value in (work if detailed else WORK).items()
    }
    doubled_material = {
        field: value * 2 if isinstance(value, (int, float)) else value
        for field, value in (material if detailed else MATERIAL).items()
    }
    assert stats["total"] == ({work_id: doubled_work} if detailed else doubled_work)
    assert stats["material_totals"] == (
        {material_id: doubled_material} if detailed else doubled_material
    )


@pytest.mark.parametrize("kind", ["objects", "project-leaders"])
@pytest.mark.parametrize("detailed", [False, True])
def test_concurrent_grouped_responses_keep_their_data(
    grouped_web, monkeypatch, kind, detailed
):
    app, _, object_repo, leader_repo, _, headers = grouped_web
    expected = {uuid4(): grouped_payload(detailed), uuid4(): grouped_payload(detailed)}
    repository = object_repo if kind == "objects" else leader_repo
    prefix = "get_object_stats" if kind == "objects" else "get_project_leader_stats"
    method = getattr(repository, prefix + ("_details" if detailed else ""))
    method.side_effect = lambda group_id: expected[group_id]
    quantity_field = work_stats_summary_model.resolved["project_work_quantity"]
    original_format = quantity_field.format
    rendezvous = Barrier(2)
    thread_state = local()

    def synchronized_format(value):
        if not getattr(thread_state, "visited", False):
            thread_state.visited = True
            rendezvous.wait(timeout=5)
        return original_format(value)

    # Detail item models share the same scalar fields as the summary model.
    monkeypatch.setattr(quantity_field, "format", synchronized_format)
    auth = headers()
    suffix = "get-stat-details" if detailed else "get-stat"

    def request_stats(group_id):
        with app.test_client() as client:
            response = client.get(f"/{kind}/{group_id}/{suffix}", headers=auth)
            assert response.status_code == 200
            return response.json["stats"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(request_stats, expected))
    assert responses == list(expected.values())


@pytest.mark.parametrize("detailed", [False, True])
def test_project_leader_cannot_read_another_leader(grouped_web, detailed):
    _, client, _, repository, _, headers = grouped_web
    suffix = "get-stat-details" if detailed else "get-stat"
    response = client.get(
        f"/project-leaders/{uuid4()}/{suffix}", headers=headers("project-leader"),
    )
    assert response.status_code == 403
    repository.get_project_leader_stats.assert_not_called()
    repository.get_project_leader_stats_details.assert_not_called()


@pytest.mark.parametrize("detailed", [False, True])
def test_missing_object_returns_404(grouped_web, detailed):
    _, client, repository, _, _, headers = grouped_web
    repository.get_object.return_value = None
    suffix = "get-stat-details" if detailed else "get-stat"
    response = client.get(f"/objects/{uuid4()}/{suffix}", headers=headers())
    assert response.status_code == 404
    repository.get_object_stats.assert_not_called()
    repository.get_object_stats_details.assert_not_called()


@pytest.mark.parametrize("query", ["offset=-1", "limit=0"])
def test_objects_collection_rejects_invalid_pagination(grouped_web, query):
    _, client, repository, _, _, headers = grouped_web
    response = client.get(f"/objects/get-stat?{query}", headers=headers())
    assert response.status_code == 400
    repository.get_all_objects_stats.assert_not_called()


def test_objects_collection_can_be_empty(grouped_web):
    _, client, repository, _, _, headers = grouped_web
    expected = {
        "total": dict.fromkeys(WORK), "material_totals": dict.fromkeys(MATERIAL, 0),
        "objects": [], "total_count": 0,
    }
    repository.get_all_objects_stats.return_value = expected
    response = client.get("/objects/get-stat", headers=headers())
    assert response.status_code == 200
    assert response.json["stats"] == expected
