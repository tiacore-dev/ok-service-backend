from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def init_db(database_url):
    
    from app.database.models import Users, Works, WorkCategories, WorkPrices, ShiftReportDetails, ShiftReports, Objects, ObjectStatuses
    from app.database.models import Projects, ProjectSchedules, ProjectWorks, Roles
    engine = create_engine(database_url, echo=False)
    Session = sessionmaker(bind=engine)
    # Создание всех таблиц
    #Base.metadata.create_all(engine)

    return engine, Session, Base