import logging
from uuid import uuid4
from app.database.models import Users
# Предполагается, что BaseDBManager в другом файле
from app.database.managers.abstract_manager import BaseDBManager


class UserManager(BaseDBManager):

    @property
    def model(self):
        return Users

    def add_user(self, login, password, name, role, created_by, category=None):
        password = str(password)  # Принудительная конвертация
        print(f"FINAL PASSWORD BEFORE HASHING: {password}")
        logging.debug(f"Тип пароля при добавлении в бд: {type(password)}")

        with self.session_scope() as session:
            new_user = self.model(
                login=login,
                name=name,
                role=role,
                category=category if category else None,
                created_by=str(created_by),
                deleted=False
            )
            new_user.set_password(password)  # Здесь хешируется
            print(f"STORED HASH: {new_user.password_hash}")  # Проверяем хеш

            try:
                session.add(new_user)
            except Exception as e:
                logging.error(f"Ошибка добавления пользователя: {e}", extra={
                    "login": "database"})
                raise

            return str(new_user.user_id)

    def create_main_admin(self,  password, category=None):
        """Добавление нового пользователя с хешированием пароля."""
        with self.session_scope() as session:
            user_id = uuid4()
            new_admin = self.model(
                user_id=user_id,
                login='admin',
                name='admin',
                role='admin',
                category=category if category else None,
                created_by=user_id,
                deleted=False
            )
            # Установим пароль сразу после создания объекта
            new_admin.set_password(password)

            try:
                session.add(new_admin)
                # При выходе из контекстного менеджера произойдёт commit
                return user_id
            except Exception as e:
                logging.error(f"Ошибка добавления пользователя: {e}",
                              extra={"login": "database"})
                raise

    def check_password_db(self, username, password):
        """Проверяем пароль пользователя"""
        with self.session_scope() as session:
            try:
                user = session.query(self.model).filter_by(
                    login=username).first()
                if user and user.check_password(password):
                    return True
                return False
            except Exception as e:
                logging.error(f"Database error in check_password: {e}")
                raise

    def update_user_password(self, user_id, new_password):
        """Обновляем пароль пользователя"""
        with self.session_scope() as session:
            user = session.query(self.model).filter_by(user_id=user_id).first()
            if user:
                user.set_password(new_password)  # Обновляем хэш пароля
                # Сессия будет закоммичена автоматически при выходе из контекстного менеджера
            else:
                logging.warning(f"Пользователь с ID {user_id} не найден",
                                extra={"login": "database"})
                return False
