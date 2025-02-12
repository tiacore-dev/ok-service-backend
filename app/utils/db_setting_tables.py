import os
from dotenv import load_dotenv


load_dotenv()


def set_admin():
    password = os.getenv('PASSWORD')
    from app.database.managers.user_manager import UserManager
    db = UserManager()
    if not db.exists(login='admin'):
        admin_id = db.create_main_admin(password=password)
        print('New admin added successfully')
        return admin_id
    else:
        admin = db.filter_one_by_dict(login='admin')
        return admin['user_id']


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
    ids = ['waiting', 'active', 'completed']
    names = ['В Ожидании', "Действующий",
             "Завершенный"]
    db.delete(
        record_id='in_progress')
    for i in range(0, 3):
        if not db.exists(object_status_id=ids[i]):
            db.add(object_status_id=ids[i], name=names[i])
