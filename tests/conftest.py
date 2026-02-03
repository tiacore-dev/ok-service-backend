import json
import os
from uuid import UUID, uuid4

import pytest
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token

from app import create_app

# Загрузка переменных окружения
load_dotenv()

# URL для тестовой базы данных PostgreSQL
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


# Глобальная переменная для хранения Base
GLOBAL_BASE = None


def create_city_for_user(db_session, user, name=None):
    """
    Helper to create a city for a given user and assign it.
    """
    from app.database.models import Cities

    city = Cities(
        city_id=uuid4(),
        name=name or f"City-{uuid4().hex[:8]}",
        created_by=user.user_id,
        deleted=False,
    )
    db_session.add(city)
    db_session.flush()
    user.city_id = city.city_id
    db_session.commit()
    db_session.refresh(user)
    return city.to_dict()


@pytest.fixture(scope="session", autouse=True)
def setup_database(test_app):
    """
    Инициализация глобальной базы данных для всех тестов.
    """
    global GLOBAL_BASE  # pylint: disable=global-statement

    from app.database.db_globals import Base, Session, engine

    GLOBAL_BASE = Base  # Сохраняем Base в глобальной переменной

    try:
        yield
    finally:
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql(
                    "ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_city_id"
                )
                conn.exec_driver_sql(
                    "ALTER TABLE users DROP CONSTRAINT IF EXISTS users_city_id_fkey"
                )
                conn.exec_driver_sql(
                    "ALTER TABLE cities DROP CONSTRAINT IF EXISTS fk_cities_created_by"
                )
                conn.exec_driver_sql(
                    "ALTER TABLE cities DROP CONSTRAINT IF EXISTS cities_created_by_fkey"
                )
        except Exception:  # pragma: no cover - cleanup best effort
            pass
        Base.metadata.drop_all(engine)
        Session.remove()  # type: ignore


@pytest.fixture(autouse=True)
def clean_db(db_session):
    """
    Автоматически очищает базу данных после каждого теста.
    """
    global GLOBAL_BASE  # pylint: disable=global-variable-not-assigned
    yield
    db_session.rollback()  # Отменяем все изменения, сделанные в тесте
    for table in reversed(
        GLOBAL_BASE.metadata.sorted_tables  # type: ignore
    ):  # Используем GLOBAL_BASE
        if table.name in {"roles", "object_statuses"}:
            continue
        db_session.execute(table.delete())
    db_session.commit()


@pytest.fixture(autouse=True)
def cleanup_scoped_session():
    yield
    from app.database.db_globals import Session

    Session.remove()


@pytest.fixture
def db_session(test_app):
    """
    Возвращает новую сессию базы данных для каждого теста.
    """
    from app.database.db_globals import Session

    session = Session()
    yield session
    session.rollback()
    session.close()
    Session.remove()


@pytest.fixture(scope="session")
def test_app():
    """
    Создаёт экземпляр Flask-приложения для тестирования с подключением к тестовой базе.
    """
    app = create_app(config_name="testing")
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URL,
        }
    )
    return app


@pytest.fixture
def client(test_app):
    """
    Возвращает тестовый клиент Flask.
    """
    return test_app.test_client()


@pytest.fixture
def jwt_token(test_app, db_session):
    """
    Генерирует JWT токен для существующего в базе пользователя.
    Если пользователя нет, создаёт нового.
    """
    from app.database.models import Users

    with test_app.app_context():
        # Поиск существующего пользователя
        user = db_session.query(Users).filter_by(login="test_admin").first()

        # Если пользователя нет, создаём его
        if not user:
            user_id = uuid4()
            user = Users(
                user_id=user_id,
                login="test_admin",
                name="Test Admin",
                role="admin",
                created_by=user_id,
                password_hash="testpassword",  # Можно заменить на захешированный пароль
                deleted=False,
            )
            # Убедитесь, что метод `set_password` доступен
            user.set_password("testpassword")
            db_session.add(user)
            db_session.commit()

        if not user.city_id:  # type: ignore
            create_city_for_user(db_session, user, name="AdminCity")

        # Генерация токена на основе реального пользователя
        token_data = {
            "login": user.login,
            "role": user.role,
            "user_id": str(user.user_id),
        }

        return create_access_token(identity=json.dumps(token_data))


@pytest.fixture
def jwt_token_admin(test_app, seed_admin):
    """
    Генерирует JWT токен для администратора.
    """
    with test_app.app_context():
        # Генерация токена на основе реального пользователя
        token_data = {
            "login": seed_admin["login"],
            "role": seed_admin["role"],
            "user_id": seed_admin["user_id"],
        }

        return create_access_token(identity=json.dumps(token_data))


@pytest.fixture
def jwt_token_user(test_app, seed_user):
    """
    Генерирует JWT токен для обычного пользователя.
    """
    with test_app.app_context():
        # Генерация токена на основе реального пользователя
        token_data = {
            "login": seed_user["login"],
            "role": seed_user["role"],
            "user_id": seed_user["user_id"],
        }

        return create_access_token(identity=json.dumps(token_data))


@pytest.fixture
def jwt_token_leader(test_app, seed_leader):
    """
    Генерирует JWT токен для обычного пользователя.
    """
    with test_app.app_context():
        # Генерация токена на основе реального пользователя
        token_data = {
            "login": seed_leader["login"],
            "role": seed_leader["role"],
            "user_id": seed_leader["user_id"],
        }

        return create_access_token(identity=json.dumps(token_data))


@pytest.fixture
def seed_user(db_session):
    """
    Добавляет тестового пользователя в базу перед тестом.
    """
    from app.database.models import Users

    user = db_session.query(Users).filter_by(login="test_user").first()
    if not user:
        user_id = uuid4()
        user = Users(
            user_id=user_id,
            login="test_user",
            name="Test User",
            role="user",
            created_by=user_id,
            deleted=False,
            city_id=None,
        )
        user.set_password("qweasdzcx")
        db_session.add(user)
        db_session.commit()
    if not user.city_id:  # type: ignore
        create_city_for_user(db_session, user)
    return user.to_dict()


@pytest.fixture
def seed_leader(db_session):
    """
    Добавляет тестового пользователя в базу перед тестом.
    """
    from app.database.models import Users

    user = db_session.query(Users).filter_by(login="test_leader").first()
    if not user:
        user_id = uuid4()
        user = Users(
            user_id=user_id,
            login="test_leader",
            name="Test Leader",
            role="project-leader",
            created_by=user_id,
            deleted=False,
            city_id=None,
        )
        user.set_password("qweasdzcx")
        db_session.add(user)
        db_session.commit()
    if not user.city_id:  # type: ignore
        create_city_for_user(db_session, user)
    return user.to_dict()


@pytest.fixture
def seed_admin(db_session):
    """
    Добавляет тестового пользователя в базу перед тестом.
    """
    from app.database.models import Users

    user = db_session.query(Users).filter_by(login="test_admin").first()
    if not user:
        user_id = uuid4()
        user = Users(
            user_id=user_id,
            login="test_admin",
            name="Test Admin",
            role="admin",
            created_by=user_id,
            deleted=False,
            city_id=None,
        )
        user.set_password("qweasdzcx")
        db_session.add(user)
        db_session.commit()
    if not user.city_id:  # type: ignore
        create_city_for_user(db_session, user)
    return user.to_dict()


@pytest.fixture
def seed_leave(db_session, seed_user, seed_leader):
    """Создает тестовый лист отсутствия."""
    from app.database.models import Leaves
    from app.database.models.leaves import AbsenceReason

    leave = Leaves(
        leave_id=uuid4(),
        user_id=UUID(seed_user["user_id"]),
        responsible_id=UUID(seed_leader["user_id"]),
        start_date=20240101,
        end_date=20240105,
        reason=AbsenceReason.VACATION,
        comment="Fixture leave",
        created_by=UUID(seed_leader["user_id"]),
        deleted=False,
    )
    db_session.add(leave)
    db_session.commit()
    return leave.to_dict()


@pytest.fixture
def seed_city(db_session, seed_admin):
    """
    Создаёт тестовый город.
    """
    from app.database.models import Cities

    city = Cities(
        city_id=uuid4(),
        name=f"FixtureCity-{uuid4().hex[:6]}",
        created_by=UUID(seed_admin["user_id"]),
        deleted=False,
    )
    db_session.add(city)
    db_session.commit()
    return city.to_dict()


@pytest.fixture
def seed_work_category(db_session, seed_user):
    """
    Добавляет тестовую категорию работы в базу перед тестом и возвращает словарь.
    """
    from app.database.models import WorkCategories

    category = WorkCategories(
        work_category_id=uuid4(), created_by=seed_user["user_id"], name="Test Category"
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
        category=UUID(seed_work_category["work_category_id"]),
        measurement_unit="units",
        created_by=seed_user["user_id"],
        deleted=False,
    )
    db_session.add(work)
    db_session.commit()
    return work.to_dict()


@pytest.fixture
def seed_work_price(db_session, seed_work, seed_user):
    """
    Добавляет тестовую цену работы в базу перед тестом.
    """
    from app.database.models import WorkPrices

    work_price = WorkPrices(
        work_price_id=uuid4(),
        work=seed_work["work_id"],
        category=1,
        price=100.00,
        created_by=seed_user["user_id"],
        deleted=False,
    )
    db_session.add(work_price)
    db_session.commit()
    return work_price.to_dict()


@pytest.fixture
def seed_material(db_session, seed_user):
    from app.database.models import Materials

    material = Materials(
        material_id=uuid4(),
        name="Test Material",
        measurement_unit="kg",
        created_by=seed_user["user_id"],
        deleted=False,
    )
    db_session.add(material)
    db_session.commit()
    return material.to_dict()


@pytest.fixture
def seed_work_material_relation(db_session, seed_work, seed_material, seed_user):
    from app.database.models import WorkMaterialRelations

    relation = WorkMaterialRelations(
        work_material_relation_id=uuid4(),
        work=seed_work["work_id"],
        material=seed_material["material_id"],
        quantity=5.5,
        created_by=seed_user["user_id"],
    )
    db_session.add(relation)
    db_session.commit()
    return relation.to_dict()


@pytest.fixture
def seed_project_material(db_session, seed_project, seed_material, seed_user):
    from app.database.models import ProjectMaterials

    record = ProjectMaterials(
        project_material_id=uuid4(),
        project=UUID(seed_project["project_id"]),
        material=UUID(seed_material["material_id"]),
        quantity=2.5,
        created_by=seed_user["user_id"],
    )
    db_session.add(record)
    db_session.commit()
    return record.to_dict()


@pytest.fixture
def seed_shift_report_material(db_session, seed_shift_report, seed_material, seed_user):
    from app.database.models import ShiftReportMaterials

    record = ShiftReportMaterials(
        shift_report_material_id=uuid4(),
        shift_report=UUID(seed_shift_report["shift_report_id"]),
        material=UUID(seed_material["material_id"]),
        quantity=1.5,
        created_by=seed_user["user_id"],
    )
    db_session.add(record)
    db_session.commit()
    return record.to_dict()


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
        created_by=seed_user["user_id"],
        city_id=UUID(seed_user["city"]),
        lng=37.6173,
        ltd=55.7558,
        deleted=False,
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
        object=UUID(seed_object["object_id"]),
        project_leader=UUID(seed_user["user_id"]),
        created_by=seed_user["user_id"],
        deleted=False,
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
        user=UUID(seed_user["user_id"]),
        date=20240101,
        date_start=20240101,
        date_end=20240101,
        project=UUID(seed_project["project_id"]),
        created_by=UUID(seed_user["user_id"]),
        signed=False,
        lng_start=37.6173,
        ltd_start=55.7558,
        lng_end=37.6174,
        ltd_end=55.7559,
        distance_start=10.5,
        distance_end=12.0,
        deleted=False,
        comment="Seed shift report comment",
    )
    db_session.add(report)
    db_session.commit()
    return report.to_dict()


@pytest.fixture
def seed_shift_reports(db_session, seed_user, seed_project):
    reports = []
    from app.database.models import ShiftReports

    for i in range(2):
        report = ShiftReports(
            shift_report_id=uuid4(),
            user=UUID(seed_user["user_id"]),
            date=20240101,
            date_start=20240101,
            date_end=20240101,
            project=UUID(seed_project["project_id"]),
            created_by=UUID(seed_user["user_id"]),
            signed=False,
            lng_start=37.6173 + i,
            ltd_start=55.7558 + i,
            lng_end=37.6174 + i,
            ltd_end=55.7559 + i,
            distance_start=10.5 + i,
            distance_end=12.0 + i,
            deleted=False,
            comment=f"Seed shift report comment {i}",
        )
        db_session.add(report)
        reports.append(report)
    db_session.commit()
    return [{"shift_report_id": str(r.shift_report_id)} for r in reports]


@pytest.fixture
def seed_shift_report_detail(
    db_session, seed_shift_report, seed_work, seed_user, seed_project_work_own
):
    from app.database.models import ShiftReportDetails

    detail = ShiftReportDetails(
        shift_report_detail_id=uuid4(),
        project_work=UUID(seed_project_work_own["project_work_id"]),
        shift_report=UUID(seed_shift_report["shift_report_id"]),
        work=UUID(seed_work["work_id"]),
        quantity=10.5,
        created_by=seed_user["user_id"],
        summ=105.0,
    )
    db_session.add(detail)
    db_session.commit()
    return detail.to_dict()


@pytest.fixture
def seed_other_leader(db_session):
    """
    Добавляет второго тестового пользователя, который будет лидером другого проекта.
    """
    from app.database.models import Users

    user = db_session.query(Users).filter_by(login="test_other_leader").first()
    if not user:
        user_id = uuid4()
        user = Users(
            user_id=user_id,
            login="test_other_leader",
            name="Test Other Leader",
            role="project-leader",
            created_by=user_id,
            deleted=False,
        )
        user.set_password("qweasdzcx")
        db_session.add(user)
        db_session.commit()
    return user.to_dict()


@pytest.fixture
def jwt_token_other_leader(test_app, seed_other_leader):
    """
    Генерирует JWT токен для второго project-leader.
    """
    with test_app.app_context():
        token_data = {
            "login": seed_other_leader["login"],
            "role": seed_other_leader["role"],
            "user_id": seed_other_leader["user_id"],
        }
        return create_access_token(identity=json.dumps(token_data))


@pytest.fixture
def seed_project_own(db_session, seed_leader, seed_object):
    """Создаёт проект, которым владеет seed_leader."""
    from app.database.models import Projects

    project_id = uuid4()
    project = Projects(
        project_id=project_id,
        name="Test Project Own",
        object=UUID(seed_object["object_id"]),
        project_leader=UUID(seed_leader["user_id"]),
        created_by=UUID(seed_leader["user_id"]),
        deleted=False,
    )
    db_session.add(project)
    db_session.commit()
    return project.to_dict()


@pytest.fixture
def seed_project_other(db_session, seed_other_leader, seed_object):
    """Создаёт проект, которым владеет seed_other_leader."""
    from app.database.models import Projects

    project_id = uuid4()
    project = Projects(
        project_id=project_id,
        name="Test Project Other",
        object=UUID(seed_object["object_id"]),
        project_leader=UUID(seed_other_leader["user_id"]),
        created_by=UUID(seed_other_leader["user_id"]),
        deleted=False,
    )
    db_session.add(project)
    db_session.commit()
    return project.to_dict()


@pytest.fixture
def seed_project_work_own(db_session, seed_project_own, seed_work):
    """Создаёт работу внутри своего проекта."""
    from app.database.models import ProjectWorks

    project_work_id = uuid4()
    project_work = ProjectWorks(
        project_work_id=project_work_id,
        project_work_name="Test project work",
        work=UUID(seed_work["work_id"]),
        project=UUID(seed_project_own["project_id"]),
        summ=0,
        quantity=0,
        created_by=UUID(seed_project_own["created_by"]),
        signed=False,
    )
    db_session.add(project_work)
    db_session.commit()
    return project_work.to_dict()


@pytest.fixture
def seed_project_work_other(db_session, seed_project_other, seed_work):
    """Создаёт работу внутри чужого проекта."""
    from app.database.models import ProjectWorks

    project_work_id = uuid4()
    project_work = ProjectWorks(
        project_work_id=project_work_id,
        project_work_name="Test project work",
        work=UUID(seed_work["work_id"]),
        project=UUID(seed_project_other["project_id"]),
        summ=0,
        quantity=0,
        created_by=UUID(seed_project_other["created_by"]),
        signed=False,
    )
    db_session.add(project_work)
    db_session.commit()
    return project_work.to_dict()


@pytest.fixture
def seed_project_schedule_own(db_session, seed_project_own, seed_work):
    """Создаёт расписание внутри своего проекта."""
    from app.database.models import ProjectSchedules

    schedule_id = uuid4()
    schedule = ProjectSchedules(
        project_schedule_id=schedule_id,
        work=UUID(seed_work["work_id"]),
        project=UUID(seed_project_own["project_id"]),
        quantity=10,
        date=20240101,
        created_by=UUID(seed_project_own["created_by"]),
    )
    db_session.add(schedule)
    db_session.commit()
    return schedule.to_dict()


@pytest.fixture
def seed_project_schedule_other(db_session, seed_project_other, seed_work):
    """Создаёт расписание внутри чужого проекта."""
    from app.database.models import ProjectSchedules

    schedule_id = uuid4()
    schedule = ProjectSchedules(
        project_schedule_id=schedule_id,
        work=UUID(seed_work["work_id"]),
        project=UUID(seed_project_other["project_id"]),
        quantity=10,
        date=20240101,
        created_by=UUID(seed_project_other["created_by"]),
    )
    db_session.add(schedule)
    db_session.commit()
    return schedule.to_dict()
