import json
from contextlib import nullcontext
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from flask_restx import Api

from app.adapters.shift_reports.mappers import (
    shift_report_dict_to_entity,
    shift_report_entity_to_response,
)
from app.adapters.shift_reports.sqlalchemy_repository import SQLAlchemyShiftReportRepository
from app.database.models import ShiftReports
from app.database.managers.shift_reports_managers import ShiftReportsManager
from app.domain.shift_reports import ShiftReportConflictError
from app.use_cases.shift_reports import UpdateShiftReportCommand
from app.web.shift_reports import routes


@pytest.fixture
def browser_web(monkeypatch):
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        JWT_SECRET_KEY="test-secret-key-with-at-least-32-bytes",
        BROWSER_ID_COOKIE_NAME="browser_id",
        BROWSER_ID_COOKIE_MAX_AGE=90 * 24 * 60 * 60,
    )
    JWTManager(app)
    Api(app).add_namespace(routes.shift_report_ns)
    user_id = uuid4()
    report = shift_report_dict_to_entity({
        "shift_report_id": str(uuid4()), "user": str(user_id), "date": 1,
        "project": str(uuid4()), "created_by": str(user_id), "created_at": 1,
        "number": 1, "start_browser_id": str(uuid4()),
        "finish_browser_id": str(uuid4()), "modified_browser_id": str(uuid4()),
    })
    repository = Mock(spec=SQLAlchemyShiftReportRepository)
    repository.get_shift_report.return_value = report

    def update(command):
        current = repository.get_shift_report.return_value
        updated = current.with_updates(modified_browser_id=command.modified_browser_id)
        repository.get_shift_report.return_value = updated
        return updated

    repository.update_shift_report.side_effect = update
    repository.get_total_sum_by_shift_report.return_value = 0
    repository.get_total_sum_by_estimate_for_shift_report.return_value = 0
    monkeypatch.setattr(routes, "_repository", lambda: repository)
    places = Mock()
    places.list_shift_place_relations.return_value = []
    monkeypatch.setattr(routes, "SQLAlchemyPlaceRelationRepository", lambda: places)
    monkeypatch.setattr(routes, "list_attachment_view_data", lambda *args: [])
    with app.app_context():
        token = create_access_token(identity=json.dumps({
            "user_id": str(user_id), "role": "user",
        }))
    return app.test_client(), repository, {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("cookie", [None, "invalid", ""])
def test_edit_creates_browser_cookie_and_reuses_it(browser_web, cookie):
    client, repository, headers = browser_web
    if cookie is not None:
        client.set_cookie("browser_id", cookie)
    report = repository.get_shift_report.return_value
    path = f"/shift_reports/{report.shift_report_id}/edit"
    response = client.patch(path, json={}, headers=headers)
    assert response.status_code == 200
    browser_id = repository.update_shift_report.call_args.args[0].modified_browser_id
    assert isinstance(browser_id, UUID)
    assert browser_id != report.modified_browser_id
    cookie_header = response.headers["Set-Cookie"]
    for attribute in [f"browser_id={browser_id}", "HttpOnly", "Secure", "SameSite=Lax", "Max-Age=7776000"]:
        assert attribute in cookie_header
    assert response.json == {
        "msg": "Shift report updated successfully",
        "shift_report_id": str(report.shift_report_id),
        "browser_id": None,
        "detail": None,
    }
    again = client.patch(path, json={"comment": "edited"}, headers=headers)
    assert again.status_code == 200
    assert "Set-Cookie" not in again.headers
    assert repository.update_shift_report.call_count == 2
    updated = repository.get_shift_report.return_value
    assert updated.modified_browser_id == browser_id
    assert updated.start_browser_id == report.start_browser_id
    assert updated.finish_browser_id == report.finish_browser_id
    assert repository.update_shift_report.call_args.args[0].updated_by == report.user


def test_edit_replaces_browser_id_and_ignores_json_override(browser_web):
    client, repository, headers = browser_web
    report = repository.get_shift_report.return_value
    for browser_id in [uuid4(), uuid4()]:
        client.set_cookie("browser_id", str(browser_id))
        response = client.patch(
            f"/shift_reports/{report.shift_report_id}/edit",
            json={"modified_browser_id": str(uuid4())}, headers=headers,
        )
        assert response.status_code == 200
        assert "Set-Cookie" not in response.headers
        assert repository.get_shift_report.return_value.modified_browser_id == browser_id


@pytest.mark.parametrize("scenario,status", [
    ("validation", 400), ("other_user", 403), ("signed", 403),
    ("leave", 409), ("missing", 404), ("save_conflict", 409), ("unauthenticated", 401),
])
def test_failed_edit_does_not_set_cookie_or_change_audit(browser_web, scenario, status):
    client, repository, headers = browser_web
    original = repository.get_shift_report.return_value
    report = original
    payload = {}
    if scenario == "validation":
        payload = {"date": -1}
    elif scenario == "other_user":
        report = original.with_updates(user=uuid4())
    elif scenario == "signed":
        report = original.with_updates(signed=True)
    elif scenario == "leave":
        report = original.with_updates(leave_id=uuid4())
    elif scenario == "missing":
        report = None
    elif scenario == "save_conflict":
        repository.update_shift_report.side_effect = ShiftReportConflictError("conflict")
    elif scenario == "unauthenticated":
        headers = {}
    repository.get_shift_report.return_value = report
    response = client.patch(
        f"/shift_reports/{original.shift_report_id}/edit", json=payload, headers=headers,
    )
    assert response.status_code == status
    assert "Set-Cookie" not in response.headers
    assert repository.get_shift_report.return_value == report
    if scenario != "save_conflict":
        repository.update_shift_report.assert_not_called()


@pytest.mark.parametrize("browser_id", [None, uuid4()])
def test_browser_id_in_read_responses_and_swagger(browser_web, browser_id):
    client, repository, headers = browser_web
    report = repository.get_shift_report.return_value.with_updates(modified_browser_id=browser_id)
    repository.get_shift_report.return_value = report
    repository.list_shift_reports.return_value = (1, [report])
    viewed = client.get(f"/shift_reports/{report.shift_report_id}/view", headers=headers)
    listed = client.get("/shift_reports/all", headers=headers)
    assert viewed.status_code == listed.status_code == 200
    expected = str(browser_id) if browser_id else None
    assert viewed.json["shift_report"]["modified_browser_id"] == expected
    assert listed.json["shift_reports"][0]["modified_browser_id"] == expected
    definitions = client.get("/swagger.json").json["definitions"]
    assert definitions["ShiftReport"]["properties"]["modified_browser_id"]["type"] == "string"
    assert "modified_browser_id" not in definitions["ShiftReportEdit"]["properties"]
    assert "modified_browser_id" not in definitions["ShiftReportCreate"]["properties"]


@pytest.mark.parametrize("browser_id", [None, uuid4()])
def test_orm_repository_and_mapper_preserve_browser_id(browser_web, browser_id):
    _, web_repository, _ = browser_web
    report = web_repository.get_shift_report.return_value
    manager = Mock()
    model = ShiftReports(
        shift_report_id=report.shift_report_id, user=report.user, project=report.project,
        created_by=report.created_by, created_at=1, date=1, number=1,
        modified_browser_id=browser_id,
    )
    payload = model.to_dict()
    expected = str(browser_id) if browser_id else None
    assert payload["modified_browser_id"] == expected
    manager.get_by_id.return_value = payload
    manager.update_shift_report.return_value = payload
    repository = SQLAlchemyShiftReportRepository(reports_manager=manager)
    updated = repository.update_shift_report(UpdateShiftReportCommand(
        shift_report_id=report.shift_report_id, modified_browser_id=browser_id,
    ))
    assert manager.update_shift_report.call_args.kwargs["modified_browser_id"] == browser_id
    assert updated is not None
    assert updated.modified_browser_id == browser_id
    assert shift_report_entity_to_response(updated)["modified_browser_id"] == expected
    assert ShiftReports.__table__.c.modified_browser_id.nullable


def test_browser_audit_migration_sql():
    path = Path(__file__).parents[1] / "alembic/versions/20261021130000_shift_report_modified_browser_id.py"
    spec = spec_from_file_location("browser_audit_migration", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    output = StringIO()
    context = MigrationContext.configure(dialect_name="postgresql", opts={
        "as_sql": True, "output_buffer": output,
    })
    with Operations.context(context):
        migration.upgrade()
        migration.downgrade()
    sql = output.getvalue()
    assert "ALTER TABLE shift_reports ADD COLUMN modified_browser_id UUID" in sql
    assert "NOT NULL" not in sql
    assert "UPDATE " not in sql
    assert "ALTER TABLE shift_reports DROP COLUMN modified_browser_id" in sql
    assert migration.down_revision == "20261021120000"


@pytest.mark.parametrize("browser_id", [None, uuid4()])
def test_manager_persists_browser_id_and_preserves_it_for_other_updates(browser_web, browser_id):
    _, web_repository, _ = browser_web
    report = web_repository.get_shift_report.return_value
    record = ShiftReports(
        shift_report_id=report.shift_report_id, user=report.user, project=report.project,
        created_by=report.created_by, created_at=1, date=1, number=1, deleted=False,
        modified_browser_id=report.modified_browser_id,
    )
    session = Mock()
    session.query.return_value.filter.return_value.first.return_value = record
    manager = ShiftReportsManager()
    manager.session_scope = Mock(return_value=nullcontext(session))
    manager._fill_missing_distances = Mock()
    manager._check_leave_conflict = Mock()
    repository = SQLAlchemyShiftReportRepository(reports_manager=manager)
    repository.get_shift_report = Mock(return_value=report)
    updated = repository.update_shift_report(UpdateShiftReportCommand(
        shift_report_id=report.shift_report_id, modified_browser_id=browser_id,
    ))
    expected = browser_id if browser_id is not None else report.modified_browser_id
    assert record.modified_browser_id == expected
    assert updated is not None and updated.modified_browser_id == expected
    session.commit.assert_called_once()
