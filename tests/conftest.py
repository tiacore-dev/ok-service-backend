import json
import os
from uuid import uuid4
import pytest
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token
from app import create_app
from app.database import set_db_globals, init_db


# Загрузка переменных окружения
load_dotenv()

# URL для тестовой базы данных PostgreSQL
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


# Глобальная переменная для хранения Base
GLOBAL_BASE = None


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    Инициализация глобальной базы данных для всех тестов.
    """
    global GLOBAL_BASE  # pylint: disable=global-statement

    # Инициализируем базу данных
    engine, Session, Base = init_db(TEST_DATABASE_URL, "testing")
    set_db_globals(engine, Session, Base)

    GLOBAL_BASE = Base  # Сохраняем Base в глобальной переменной

    yield  # Фикстура активна на протяжении всех тестов

    # Удаляем таблицы после завершения тестов
    Base.metadata.drop_all(engine)
    Session.remove()


@pytest.fixture(autouse=True)
def clean_db(db_session):
    """
    Автоматически очищает базу данных после каждого теста.
    """
    global GLOBAL_BASE  # pylint: disable=global-variable-not-assigned
    yield
    db_session.rollback()  # Отменяем все изменения, сделанные в тесте
    for table in reversed(GLOBAL_BASE.metadata.sorted_tables):  # Используем GLOBAL_BASE
        db_session.execute(table.delete())
    db_session.commit()


@pytest.fixture
def db_session():
    """
    Возвращает новую сессию базы данных для каждого теста.
    """
    from app.database.db_globals import Session
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_app(db_session):
    """
    Создаёт экземпляр Flask-приложения для тестирования с подключением к тестовой базе.
    """
    app = create_app(config_name="testing")
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": TEST_DATABASE_URL,
    })

    # Передаем тестовую сессию в приложение
    app.dependency_overrides = {
        "db_session": lambda: db_session
    }
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
            user = Users(
                user_id=uuid4(),
                login="test_admin",
                name="Test Admin",
                role="admin",
                password_hash="testpassword",  # Можно заменить на захешированный пароль
                deleted=False
            )
            # Убедитесь, что метод `set_password` доступен
            user.set_password("testpassword")
            db_session.add(user)
            db_session.commit()

        # Генерация токена на основе реального пользователя
        token_data = {
            "login": user.login,
            "role": user.role,
            "user_id": str(user.user_id)
        }

        return create_access_token(identity=json.dumps(token_data))


@pytest.fixture
def jwt_token_admin(test_app):
    """
    Генерирует JWT токен для администратора.
    """
    with test_app.app_context():
        return create_access_token(identity=json.dumps({"login": "admin_user", "role": "admin", "user_id": "f83d4538-2e1b-49cc-80ae-16c9bcf58f6e"}))


@pytest.fixture
def jwt_token_user(test_app):
    """
    Генерирует JWT токен для обычного пользователя.
    """
    with test_app.app_context():
        return create_access_token(identity=json.dumps({"login": "regular_user", "role": "user", "user_id": "f83d4538-2e1b-49cc-80ae-16c9bcf58f6e"}))
