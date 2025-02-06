# Tests for ShiftReports
from uuid import uuid4, UUID
import logging
import pytest

logger = logging.getLogger('ok_service')


@pytest.fixture
def seed_user(db_session):
    """
    Add a test user to the database.
    """
    from app.database.models import Users
    user = Users(
        user_id=uuid4(),
        login="test_user",
        password_hash="test_hash",
        name="Test User",
        role="user",
        category=1,
        deleted=False
    )
    db_session.add(user)
    db_session.commit()
    return user.to_dict()


@pytest.fixture
def seed_work_category(db_session, seed_user):
    """
    Добавляет тестовую категорию работы в базу перед тестом и возвращает словарь.
    """
    from app.database.models import WorkCategories
    category = WorkCategories(
        work_category_id=uuid4(),
        created_by=seed_user['user_id'],
        name="Test Category"
    )
    db_session.add(category)
    db_session.commit()
    return category.to_dict()


@pytest.fixture
def seed_work(db_session, seed_work_category, seed_user):
    from app.database.models import Works
    work = Works(
        work_id=uuid4(),
        name="Test Work",
        category=UUID(seed_work_category['work_category_id']),
        measurement_unit="units",
        created_by=seed_user['user_id'],
        deleted=False
    )
    db_session.add(work)
    db_session.commit()
    return work.to_dict()


@pytest.fixture
def seed_object(db_session, seed_user):
    """
    Добавляет тестовый объект в базу перед тестом.
    """
    from app.database.models import Objects
    obj = Objects(
        object_id=uuid4(),
        name="Test Object",
        address="123 Test St",
        description="Test description",
        status="active",
        created_by=seed_user['user_id'],
        deleted=False
    )
    db_session.add(obj)
    db_session.commit()
    obj_data = obj.to_dict()
    return obj_data


@pytest.fixture
def seed_project(db_session, seed_user, seed_object):
    """
    Add a test project to the database.
    """
    from app.database.models import Projects
    project = Projects(
        project_id=uuid4(),
        name="Test Project",
        object=UUID(seed_object['object_id']),
        project_leader=UUID(seed_user['user_id']),
        created_by=seed_user['user_id'],
        deleted=False
    )
    db_session.add(project)
    db_session.commit()
    return project.to_dict()


@pytest.fixture
def seed_shift_report(db_session, seed_user, seed_project):
    """
    Add a test shift report to the database.
    """
    from app.database.models import ShiftReports
    report = ShiftReports(
        shift_report_id=uuid4(),
        user=UUID(seed_user['user_id']),
        date=20240101,
        project=UUID(seed_project['project_id']),
        created_by=seed_user['user_id'],
        signed=False,
        deleted=False
    )
    db_session.add(report)
    db_session.commit()
    return report.to_dict()


@pytest.fixture
def seed_shift_report_detail(db_session, seed_shift_report, seed_work, seed_user):
    from app.database.models import ShiftReportDetails
    detail = ShiftReportDetails(
        shift_report_detail_id=uuid4(),
        shift_report=UUID(seed_shift_report['shift_report_id']),
        work=UUID(seed_work['work_id']),
        quantity=10.5,
        created_by=seed_user['user_id'],
        summ=105.0
    )
    db_session.add(detail)
    db_session.commit()
    return detail.to_dict()


def test_add_shift_report(client, jwt_token, seed_user, seed_project, seed_shift_report_detail):
    """
    Test adding a new shift report via API.
    """
    data = {
        "user": seed_user['user_id'],
        "date": 20240102,
        "project": seed_project['project_id'],
        "signed": True,
        "details": [{
            "work": seed_shift_report_detail['work'],
            "summ": seed_shift_report_detail['summ'],
            "quantity": seed_shift_report_detail['quantity']
        }]
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.post("/shift_reports/add", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "New shift report added successfully"

    from app.database.models import ShiftReports
    with client.application.app_context():
        from app.database.db_globals import Session
        session = Session()
        report = session.query(ShiftReports).filter_by(date=20240102).first()
        assert report is not None
        assert str(report.user) == seed_user['user_id']
        assert str(report.project) == seed_project['project_id']
        assert report.signed is True


def test_view_shift_report(client, jwt_token, seed_shift_report, seed_user, seed_project):
    """
    Test viewing a shift report via API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.get(
        f"/shift_reports/{str(seed_shift_report['shift_report_id'])}/view", headers=headers)

    assert response.status_code == 200
    assert "shift_report" in response.json
    assert response.json["msg"] == "Shift report found successfully"
    assert response.json["shift_report"]["user"] == seed_user['user_id']
    assert response.json["shift_report"]["project"] == seed_project['project_id']
    assert response.json["shift_report"]["date"] == seed_shift_report['date']
    assert response.json["shift_report"]["signed"] == seed_shift_report['signed']


def test_soft_delete_shift_report(client, jwt_token, seed_shift_report):
    """
    Test soft deleting a shift report via API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/shift_reports/{str(seed_shift_report['shift_report_id'])}/delete/soft", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Shift report {
        str(seed_shift_report['shift_report_id'])} soft deleted successfully"

    from app.database.models import ShiftReports
    with client.application.app_context():
        from app.database.db_globals import Session
        session = Session()
        report = session.query(ShiftReports).filter_by(
            shift_report_id=seed_shift_report['shift_report_id']).first()
        assert report is not None
        assert report.deleted is True


def test_hard_delete_shift_report(client, jwt_token, seed_shift_report, db_session):
    """
    Test hard deleting a shift report.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.delete(
        f"/shift_reports/{str(seed_shift_report['shift_report_id'])}/delete/hard", headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == f"Shift report {
        str(seed_shift_report['shift_report_id'])} hard deleted successfully"

    from app.database.models import ShiftReports
    obj = db_session.query(ShiftReports).filter_by(
        shift_report_id=seed_shift_report['shift_report_id']).first()
    assert obj is None


def test_edit_shift_report(client, jwt_token, seed_shift_report):
    """
    Test editing a shift report via API.
    """
    data = {
        "date": 20240103,
        "signed": True
    }
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = client.patch(
        f"/shift_reports/{str(seed_shift_report['shift_report_id'])}/edit", json=data, headers=headers)

    assert response.status_code == 200
    assert response.json["msg"] == "Shift report updated successfully"

    from app.database.models import ShiftReports
    with client.application.app_context():
        from app.database.db_globals import Session
        session = Session()
        report = session.query(ShiftReports).filter_by(
            shift_report_id=UUID(seed_shift_report['shift_report_id'])).first()
        assert report is not None
        assert report.date == 20240103
        assert report.signed is True


def test_get_all_shift_reports_with_filters(client, jwt_token, seed_shift_report, seed_user, seed_project):
    """
    Test fetching all shift reports with filters via API.
    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    params = {
        "user": seed_user['user_id'],
        "date": seed_shift_report['date'],
        "project": seed_project['project_id'],
        "deleted": False
    }
    logger.info(f'Отправляемые параметры: {params}')
    response = client.get("/shift_reports/all",
                          query_string=params, headers=headers)

    assert response.status_code == 200
    assert "shift_reports" in response.json
    assert response.json["msg"] == "Shift reports found successfully"

    shift_reports = response.json["shift_reports"]
    assert len(shift_reports) > 0
    assert any(report["shift_report_id"] == seed_shift_report['shift_report_id']
               for report in shift_reports)
    assert shift_reports[0]["user"] == seed_user['user_id']
    assert shift_reports[0]["project"] == seed_project['project_id']
    assert shift_reports[0]["date"] == seed_shift_report['date']
    assert shift_reports[0]["signed"] == seed_shift_report['signed']
