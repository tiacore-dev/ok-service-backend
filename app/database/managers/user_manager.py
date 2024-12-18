from app.database.models import Users
# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager


class UserManager(BaseDBManager):

    @property
    def model(self):
        return Users

    def add_user(self, login, password, name, role, category=None):
        """Добавление нового пользователя с хешированием пароля."""
        with self.session_scope() as session:
            new_user = self.model(
                login=login,
                name=name,
                role=role,
                category=category if category else None,
                deleted=False
            )
            # Установим пароль сразу после создания объекта
            new_user.set_password(password)

            session.add(new_user)
            # При выходе из контекстного менеджера произойдёт commit
            return new_user

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
