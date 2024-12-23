def set_roles():
    from app.database.managers.roles_managers import RolesManager
    db = RolesManager()

    ids = ['user', 'admin', 'manager', 'project-leader']
    names = ['Пользователь', "Администратор",
             "Менеджер", "Руководитель проекта"]

    for i in range(0, 4):
        if not db.exists(role_id=ids[i]):
            db.add(role_id=ids[i], name=names[i])
