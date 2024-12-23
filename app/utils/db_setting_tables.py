import os
from dotenv import load_dotenv


load_dotenv()


def set_admin():
    password = os.getenv('PASSWORD')
    login = os.getenv('LOGIN')
    username = 'admin'
    from app.database.managers.user_manager import UserManager
    db = UserManager()
    if not db.exists(login=login):
        db.add_user(login=login, password=password,
                    name=username, role='admin')
        print('New admin added successfully')


def set_roles():
    from app.database.managers.roles_managers import RolesManager
    db = RolesManager()

    ids = ['user', 'admin', 'manager', 'project-leader']
    names = ['Пользователь', "Администратор",
             "Менеджер", "Руководитель проекта"]

    for i in range(0, 4):
        if not db.exists(role_id=ids[i]):
            db.add(role_id=ids[i], name=names[i])


def set_object_status():
    from app.database.managers.objects_managers import ObjectStatusesManager
    db = ObjectStatusesManager()
    if not db.exists(object_status_id='in_progress'):
        db.add(
            object_status_id='in_progress',
            name="Active"
        )
