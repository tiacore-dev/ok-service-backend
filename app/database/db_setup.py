from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def init_db(database_url, config_name):
    engine = create_engine(
        database_url,
        echo=False,
        pool_size=10,  # Размер пула соединений
        max_overflow=20,  # Максимальное количество дополнительных соединений
        pool_timeout=30,  # Время ожидания доступного соединения (сек)
        pool_recycle=1800,  # Перезапуск соединения каждые 30 минут
        pool_pre_ping=True  # Проверка соединения перед выдачей из пула
    )
    session_factory = sessionmaker(
        bind=engine, autocommit=False, autoflush=False)  # Для тестов
    Session = scoped_session(session_factory)

    if config_name == "testing":
      # Для тестов
        from app.database.models import Users, ObjectStatuses, Logs, Roles  # pylint: disable=unused-import
        Base.metadata.create_all(engine)
        # Создание всех таблиц

    return engine, Session, Base
