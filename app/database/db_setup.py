from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def init_db(database_url, config_name):
    engine = create_engine(database_url, echo=False)
    # Session = sessionmaker(bind=engine) #Для прода
    session_factory = sessionmaker(bind=engine)  # Для тестов
    Session = scoped_session(session_factory)  # Для тестов
    if config_name == "testing":
        from app.database.models import Users, ObjectStatuses, Logs, Roles  # pylint: disable=unused-import
        # Создание всех таблиц
        Base.metadata.create_all(engine)

    return engine, Session, Base
