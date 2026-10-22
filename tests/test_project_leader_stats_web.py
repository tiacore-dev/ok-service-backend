import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local
from unittest.mock import Mock
from uuid import uuid4

import pytest
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from flask_restx import Api, fields, marshal

from app.adapters.projects import SQLAlchemyProjectRepository
from app.routes.models.place_models import place_model
from app.web.objects.models import (
    _MonthlyStatistics,
    object_stats_collection_response,
    project_leader_fact_item,
)
from app.web.objects.routes import object_ns
from app.web.project_leaders import routes


@pytest.fixture
def leaders_web(monkeypatch):
    app = Flask(__name__)
    app.config.update(
        TESTING=True, JWT_SECRET_KEY="test-secret-key-with-at-least-32-bytes"
    )
    JWTManager(app)
    api = Api(app)
    api.add_namespace(object_ns)
    api.add_namespace(routes.project_leader_ns)
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


def monthly_stats(value):
    return {
        "2026-09": {
            "shift_report_details_quantity": value,
            "shift_report_details_summ": value * 100,
            "shift_report_details_summ_by_estimate": value * 120,
        },
        "2026-10": {
            "shift_report_details_quantity": 0,
            "shift_report_details_summ": 0,
            "shift_report_details_summ_by_estimate": 0,
        },
    }


def monthly_material_stats(value):
    return {
        "2026-09": {
            "shift_report_material_quantity": value,
            "shift_report_material_summ_by_estimate": value * 50,
        },
        "2026-10": {
            "shift_report_material_quantity": 0,
            "shift_report_material_summ_by_estimate": 0,
        },
    }


def payload():
    leaders = []
    for value in (1.5, 2.5):
        leaders.append(
            {
                "user_id": str(uuid4()),
                "login": f"leader-{value}",
                "name": f"Прораб {value}",
                "stats": monthly_stats(value),
                "material_stats": monthly_material_stats(value),
                "projects": [
                    {
                        "project_id": str(uuid4()),
                        "name": "Спецификация",
                        "stats": monthly_stats(value),
                        "material_stats": monthly_material_stats(value),
                    }
                ],
            }
        )
    return {
        "total": monthly_stats(4),
        "material_totals": monthly_material_stats(4),
        "project_leaders": leaders,
        "total_count": 2,
    }


@pytest.mark.parametrize("role", ["admin", "manager", "project-leader"])
def test_monthly_http_response_preserves_values_at_every_level(leaders_web, role):
    app, client, repository = leaders_web
    expected = payload()
    repository.get_all_project_leaders_fact_stats.return_value = expected

    # Repeated calls also guard against state leaking between shared Wildcard fields.
    for _ in range(2):
        response = client.get("/project-leaders/get-stat", headers=headers(app, role))
        assert response.status_code == 200
        assert response.json == {
            "msg": "Project leaders stats fetched successfully",
            "stats": expected,
        }


@pytest.mark.parametrize("with_leader", [False, True])
def test_empty_monthly_maps_remain_empty(leaders_web, with_leader):
    app, client, repository = leaders_web
    expected = payload()
    expected.update(total={}, material_totals={})
    if with_leader:
        for leader in expected["project_leaders"]:
            leader.update(stats={}, material_stats={})
            for project in leader["projects"]:
                project.update(stats={}, material_stats={})
        expected["project_leaders"][1]["projects"] = []
    else:
        expected.update(project_leaders=[], total_count=0)
    repository.get_all_project_leaders_fact_stats.return_value = expected

    response = client.get("/project-leaders/get-stat", headers=headers(app))

    assert response.status_code == 200
    assert response.json["stats"] == expected


def test_monthly_response_preserves_null_values(leaders_web):
    app, client, repository = leaders_web
    expected = payload()
    expected["total"]["2026-09"]["shift_report_details_summ"] = None
    expected["material_totals"]["2026-09"][
        "shift_report_material_summ_by_estimate"
    ] = None
    repository.get_all_project_leaders_fact_stats.return_value = expected

    response = client.get("/project-leaders/get-stat", headers=headers(app))

    assert response.status_code == 200
    assert response.json["stats"] == expected


@pytest.mark.parametrize(
    "query",
    ["offset=-1", "limit=0", "date_from=200&date_to=100", "project_leader_ids=bad"],
)
def test_invalid_filters_are_rejected_before_reading_stats(leaders_web, query):
    app, client, repository = leaders_web

    response = client.get(
        f"/project-leaders/get-stat?{query}", headers=headers(app)
    )

    assert response.status_code == 400
    repository.get_all_project_leaders_fact_stats.assert_not_called()


@pytest.mark.parametrize("role,status", [(None, 401), ("user", 403)])
def test_unauthorized_requests_do_not_read_stats(leaders_web, role, status):
    app, client, repository = leaders_web

    response = client.get(
        "/project-leaders/get-stat", headers=headers(app, role) if role else {}
    )

    assert response.status_code == status
    repository.get_all_project_leaders_fact_stats.assert_not_called()


def test_swagger_describes_month_maps_at_every_level(leaders_web):
    _, client, _ = leaders_web
    response = client.get("/swagger.json")
    assert response.status_code == 200
    definitions = response.json["definitions"]
    for model, work_field, material_field in (
        ("ProjectLeaderStatsCollectionPayload", "total", "material_totals"),
        ("ProjectLeaderStatsCollectionItem", "stats", "material_stats"),
        ("ProjectLeaderFactProject", "stats", "material_stats"),
    ):
        for field, item_model in (
            (work_field, "ProjectLeaderFactStats"),
            (material_field, "ProjectLeaderMaterialFactStats"),
        ):
            field_schema = definitions[model]["properties"][field]
            assert field_schema == {
                "type": "object",
                "additionalProperties": {"$ref": f"#/definitions/{item_model}"},
            }


def test_concurrent_http_responses_keep_their_own_months(leaders_web, monkeypatch):
    app, _, repository = leaders_web
    expected = {
        1: payload(),
        2: json.loads(
            json.dumps(payload()).replace("2026-09", "2025-01").replace(
                "2026-10", "2025-02"
            )
        ),
    }
    repository.get_all_project_leaders_fact_stats.side_effect = (
        lambda query: expected[query.date_from]
    )
    rendezvous = Barrier(2)
    thread_state = local()
    quantity_field = project_leader_fact_item.resolved["shift_report_details_quantity"]
    original_format = quantity_field.format

    def synchronized_format(value):
        # Interleave month traversal, including Wildcard's second marshalling pass.
        visits = getattr(thread_state, "visits", 0)
        if visits < 2:
            thread_state.visits = visits + 1
            rendezvous.wait(timeout=5)
        return original_format(value)

    monkeypatch.setattr(quantity_field, "format", synchronized_format)
    auth = headers(app)

    def request_stats(request_id):
        with app.test_client() as client:
            response = client.get(
                f"/project-leaders/get-stat?date_from={request_id}", headers=auth
            )
            assert response.status_code == 200
            return response.json

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(request_stats, (1, 2)))

    for request_id, response in enumerate(responses, start=1):
        assert response["stats"] == expected[request_id]


@pytest.mark.parametrize("model", [None, {}])
def test_monthly_schema_requires_a_named_model(model):
    with pytest.raises(fields.MarshallingError, match="require a named Model"):
        _MonthlyStatistics(model).schema()


def test_object_collection_keeps_flat_summary():
    stats = {
        "total": {"shift_report_details_quantity": 12.5},
        "material_totals": {"shift_report_material_quantity": 3},
        "objects": [],
        "total_count": 0,
    }
    response = marshal({"stats": stats}, object_stats_collection_response)
    assert isinstance(response, dict)
    result = response["stats"]
    assert isinstance(result, dict)
    total = result["total"]
    material_totals = result["material_totals"]
    assert isinstance(total, dict)
    assert isinstance(material_totals, dict)
    assert total["shift_report_details_quantity"] == 12.5
    assert material_totals["shift_report_material_quantity"] == 3
    assert result["objects"] == []
