import json
import os
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
    global GLOBAL_BASE  # pylint: disable=global-statement
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
def jwt_token(test_app):
    """
    Генерирует JWT токен для тестового пользователя.
    """
    with test_app.app_context():
        return create_access_token(identity=json.dumps({"login": "test_admin", "role": "admin"}))
