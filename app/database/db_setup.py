from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def init_db(database_url):
    engine = create_engine(database_url, echo=False)
    Session = sessionmaker(bind=engine)
    # Создание всех таблиц
    # Base.metadata.create_all(engine)

    return engine, Session, Base
