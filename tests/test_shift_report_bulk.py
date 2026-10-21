from decimal import Decimal
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from app.adapters.shift_reports import SQLAlchemyShiftReportRepository
from app.database.models import (
    ProjectWorks,
    ShiftReportDetails,
    ShiftReportMaterials,
    ShiftReports,
)


@pytest.fixture
def bulk_payload(seed_user, seed_leader, seed_project):
    return {
        "user_ids": [seed_leader["user_id"], seed_user["user_id"]],
        "date": 20240102,
        "project": seed_project["project_id"],
        "date_start": None,
        "date_end": None,
        "night_shift": True,
        "extreme_conditions": False,
        "short_shift": False,
        "signed": False,
        "comment": "Общая смена",
    }


@pytest.fixture
def bulk_details(bulk_payload, seed_work, seed_work_price, db_session, seed_admin):
    work = ProjectWorks(
        project_work_id=uuid4(),
        project=UUID(bulk_payload["project"]),
        work=UUID(seed_work["work_id"]),
        quantity=100,
        created_by=UUID(seed_admin["user_id"]),
    )
    db_session.add(work)
    db_session.commit()
    bulk_payload["details"] = [
        {
            "project_work": str(work.project_work_id),
            "work": seed_work["work_id"],
            "quantity": 2,
        }
    ]
    return bulk_payload


def post(client, jwt_token_admin, payload):
    return client.post(
        "/shift_reports/add-bulk",
        json=payload,
        headers={"Authorization": f"Bearer {jwt_token_admin}"},
    )


def test_bulk_creates_reports_and_details_in_input_order(
    client, jwt_token_admin, seed_admin, bulk_details, db_session
):
    bulk_details["user_ids"] *= 2
    response = post(client, jwt_token_admin, bulk_details)
    assert response.status_code == 200, response.json
    ids = response.json["shift_report_ids"]
    assert len(ids) == 2 and len(set(ids)) == 2
    for report_id, user_id in zip(ids, bulk_details["user_ids"][:2]):
        report = db_session.get(ShiftReports, UUID(report_id))
        assert str(report.user) == user_id
        assert str(report.created_by) == seed_admin["user_id"]
        assert report.comment == bulk_details["comment"]
        assert report.night_shift is True
        assert report.extreme_conditions is False
        assert report.short_shift is False
        assert report.signed is False
        assert report.date_start is None and report.date_end is None
        detail = (
            db_session.query(ShiftReportDetails)
            .filter_by(shift_report=report.shift_report_id)
            .one()
        )
        assert detail.quantity == Decimal(2)
        assert str(detail.project_work) == bulk_details["details"][0]["project_work"]
    assert db_session.query(ShiftReports).count() == 2
    assert db_session.query(ShiftReportDetails).count() == 2


@pytest.mark.parametrize("user_ids", [[], None, "not-a-list", ["bad-uuid"], [None]])
def test_bulk_rejects_invalid_list(
    client, jwt_token_admin, bulk_payload, db_session, user_ids
):
    bulk_payload["user_ids"] = user_ids
    response = post(client, jwt_token_admin, bulk_payload)
    assert response.status_code == 400, response.json
    assert "user_ids" in response.json["error"]
    assert db_session.query(ShiftReports).count() == 0


def test_bulk_requires_user_ids(client, jwt_token_admin, bulk_payload):
    del bulk_payload["user_ids"]
    assert post(client, jwt_token_admin, bulk_payload).status_code == 400


def test_bulk_unknown_user_rejects_whole_request(
    client, jwt_token_admin, bulk_payload, db_session
):
    bulk_payload["user_ids"].append(str(uuid4()))
    assert post(client, jwt_token_admin, bulk_payload).status_code == 400
    assert db_session.query(ShiftReports).count() == 0


def test_bulk_leave_conflict_rolls_back_first_report_and_details(
    client, jwt_token_admin, bulk_details, seed_leave, db_session, monkeypatch
):
    statistics = Mock()
    monkeypatch.setattr(
        "app.web.shift_reports.routes._repository",
        lambda: SQLAlchemyShiftReportRepository(statistics=statistics),
    )
    response = post(client, jwt_token_admin, bulk_details)
    assert response.status_code == 409, response.json
    assert db_session.query(ShiftReports).count() == 0
    assert db_session.query(ShiftReportDetails).count() == 0
    assert db_session.query(ShiftReportMaterials).count() == 0
    statistics.recalculate_many.assert_not_called()


def test_bulk_error_in_second_detail_rolls_back_everything(
    client, jwt_token_admin, bulk_details, db_session, monkeypatch
):
    from app.database.managers.shift_reports_managers import ShiftReportsDetailsManager
    from app.domain.shift_reports import ShiftReportConflictError

    calls = []
    original = ShiftReportsDetailsManager._sync_shift_report_materials

    def sync(session, detail, created_by):
        calls.append(detail.shift_report)
        original(session, detail, created_by)
        if len(calls) == 2:
            raise ShiftReportConflictError("Second detail conflict")

    monkeypatch.setattr(
        ShiftReportsDetailsManager, "_sync_shift_report_materials", staticmethod(sync)
    )
    response = post(client, jwt_token_admin, bulk_details)
    assert response.status_code == 409, response.json
    assert len(calls) == 2
    assert db_session.query(ShiftReports).count() == 0
    assert db_session.query(ShiftReportDetails).count() == 0


def test_bulk_user_forbidden(client, jwt_token_user, bulk_payload, db_session):
    response = post(client, jwt_token_user, bulk_payload)
    assert response.status_code == 403
    assert db_session.query(ShiftReports).count() == 0


def test_bulk_requires_authentication(client, bulk_payload):
    assert client.post("/shift_reports/add-bulk", json=bulk_payload).status_code == 401


def test_bulk_rejects_project_not_in_progress(
    client, jwt_token_admin, bulk_payload, db_session
):
    from app.database.models import Projects

    project = db_session.get(Projects, UUID(bulk_payload["project"]))
    project.status = "pending"
    db_session.commit()
    assert post(client, jwt_token_admin, bulk_payload).status_code == 409
    assert db_session.query(ShiftReports).count() == 0


def test_bulk_rejects_invalid_dates(client, jwt_token_admin, bulk_payload, db_session):
    bulk_payload.update(date_start=10, date_end=9)
    assert post(client, jwt_token_admin, bulk_payload).status_code == 400
    assert db_session.query(ShiftReports).count() == 0


def test_bulk_without_details(client, jwt_token_admin, bulk_payload, db_session):
    response = post(client, jwt_token_admin, bulk_payload)
    assert response.status_code == 200, response.json
    assert len(response.json["shift_report_ids"]) == 2
    assert db_session.query(ShiftReportDetails).count() == 0


def test_bulk_swagger_and_permission(client):
    from app.utils.api_key_permissions import API_KEY_PERMISSIONS

    assert (
        "shift-reports-create-bulk",
        "POST /shift_reports/add-bulk",
    ) in API_KEY_PERMISSIONS
    swagger = client.get("/swagger.json").json
    model = swagger["definitions"]["ShiftReportBulkCreate"]
    assert "user" not in model["properties"]
    assert "user_ids" in model["required"]
    assert model["properties"]["user_ids"]["minItems"] == 1
    assert model["properties"]["user_ids"]["type"] == "array"
    assert model["properties"]["user_ids"]["items"]["type"] == "string"
    assert "details" in model["properties"]
    assert "post" in swagger["paths"]["/shift_reports/add-bulk"]


@pytest.mark.parametrize(
    "permission_code", ["shift-reports-create-bulk", "shift-reports-create", None]
)
def test_bulk_api_key_requires_exact_permission(
    client, db_session, seed_admin, bulk_payload, permission_code
):
    from app.database.models import ApiKeys, KeyPermissionTypeRelations, PermissionTypes
    from app.utils.api_key_permissions import set_api_key_permissions

    set_api_key_permissions()
    key = ApiKeys(api_key_id=uuid4(), name="bulk-key", token=str(uuid4()))
    db_session.add(key)
    if permission_code:
        permission = (
            db_session.query(PermissionTypes).filter_by(code=permission_code).one()
        )
        db_session.add(
            KeyPermissionTypeRelations(
                api_key_id=key.api_key_id,
                permission_type_id=permission.permission_type_id,
            )
        )
    db_session.commit()
    response = client.post(
        "/shift_reports/add-bulk", json=bulk_payload, headers={"API-Key": key.token}
    )
    assert response.status_code == (
        200 if permission_code == "shift-reports-create-bulk" else 403
    ), response.json
    assert db_session.query(ShiftReports).count() == (
        2 if permission_code == "shift-reports-create-bulk" else 0
    )


@pytest.mark.parametrize("role", ["manager", "project-leader", "accountant"])
def test_bulk_short_shift_role_gate(client, test_app, seed_admin, bulk_payload, role):
    import json

    from flask_jwt_extended import create_access_token

    with test_app.app_context():
        token = create_access_token(
            identity=json.dumps({"user_id": seed_admin["user_id"], "role": role})
        )
    response = post(client, token, bulk_payload)
    assert response.status_code == (403 if role == "accountant" else 200), response.json


def test_bulk_normalizes_uuid_duplicates(client, jwt_token_admin, bulk_payload):
    bulk_payload["user_ids"] += [item.upper() for item in bulk_payload["user_ids"]]
    response = post(client, jwt_token_admin, bulk_payload)
    assert response.status_code == 200, response.json
    assert len(response.json["shift_report_ids"]) == 2
