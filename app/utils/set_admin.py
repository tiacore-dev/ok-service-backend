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
