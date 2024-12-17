from app.models import Users
from app.database.managers.abstract_manager import BaseDBManager  # Предполагается, что BaseDBManager в другом файле


class UserManager(BaseDBManager):

    @property
    def model(self):
        return Users

    def check_password(self, username, password):
        """Проверяем пароль пользователя"""
        with self.session_scope() as session:
            user = session.query(self.model).filter_by(login=username).first()
            if user and user.check_password(password):
                return True
            return False

    def update_user_password(self, username, new_password):
        """Обновляем пароль пользователя"""
        with self.session_scope() as session:
            user = session.query(self.model).filter_by(login=username).first()
            if user:
                user.set_password(new_password)  # Обновляем хэш пароля
                # Сессия будет закоммичена автоматически при выходе из контекстного менеджера
