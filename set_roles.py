"""id: user, name: Пользователь
id: admin, name: Администратор
id: manager, name: Менеджер
id: project-leader name: Руководитель проекта"""

from app.database.managers.roles_managers import RolesManager
import os
from dotenv import load_dotenv
from app.database import init_db, set_db_globals

load_dotenv()

database_url = os.getenv('DATABASE_URL')

engine, Session, Base = init_db(database_url)

# Установка глобальных переменных для работы с базой данных
set_db_globals(engine, Session, Base)


db = RolesManager()

ids = ['user', 'admin', 'manager', 'project-leader']
names = ['Пользователь', "Администратор", "Менеджер", "Руководитель проекта"]

for i in range(0, 4):
    if not db.exists(role_id=ids[i]):
        db.add(role_id=ids[i], name=names[i])
