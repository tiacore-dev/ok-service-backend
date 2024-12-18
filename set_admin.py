from app.database.managers.user_manager import UserManager
import os
from dotenv import load_dotenv
from app.database import init_db, set_db_globals

load_dotenv()

password = os.getenv('PASSWORD')
login = os.getenv('LOGIN')
database_url = os.getenv('DATABASE_URL')
username = 'admin'
engine, Session, Base = init_db(database_url)

# Установка глобальных переменных для работы с базой данных
set_db_globals(engine, Session, Base)


db = UserManager()


if not db.exists(login=login):
    db.add_user(login=login, password=password, name=username, role='admin')
    print('New admin added successfully')
