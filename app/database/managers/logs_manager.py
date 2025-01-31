import logging
from datetime import timedelta, datetime
from app.database.models.logs import Logs
from app.database.db_globals import Session


logger = logging.getLogger('ok_service')


class LogManager():
    def __init__(self):
        self.Session = Session

    def add_logs(self, login, action, message):
        """Добавление лога."""
        session = self.Session()
        try:
            new_record = Logs(login=login, action=action,
                              message=message)  # Создаем объект Logs
            session.add(new_record)  # Добавляем новый лог через сессию
            session.commit()  # Не забудьте зафиксировать изменения в базе данных
            return new_record
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка в сессии: {e}", extra={
                "login": "database"})
            raise
        finally:
            session.close()
            logger.debug(f"""Сессия закрыта""", extra={"login": "database"})

    def get_logs_by_date(self, date, offset=0, limit=10):
        """Получение логов по дате."""
        session = self.Session()
        try:
            return session.query(Logs).filter(Logs.timestamp >= date, Logs.timestamp < date + timedelta(days=1)).offset(offset).limit(limit).all()
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка в сессии: {e}", extra={
                "login": "database"})
            raise
        finally:
            session.close()
            logger.debug(f"""Сессия закрыта""", extra={"login": "database"})

    def filter_by_date(self, user_id=None, date=None, offset=0, limit=10):
        """Фильтрация логов по дате и ID пользователя."""
        session = self.Session()
        try:
            query = session.query(Logs)
            if user_id:
                query = query.filter(Logs.user_id == user_id)
            if date:
                # Конвертация строки даты в объект datetime
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                query = query.filter(Logs.timestamp >= date_obj,
                                     Logs.timestamp < date_obj + timedelta(days=1))
            return query.offset(offset).limit(limit).all()
        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка в сессии: {e}", extra={
                "login": "database"})
            raise
        finally:
            session.close()
            logger.debug(f"""Сессия закрыта""", extra={"login": "database"})

    def get_logs(self, user_id=None, date=None, offset=0, limit=10):
        """Получение логов с фильтрацией и пагинацией."""
        session = self.Session()
        try:
            query = session.query(Logs)

            # Фильтрация по user_id, если указано
            if user_id:
                query = query.filter(Logs.user_id == user_id)

            # Фильтрация по дате, если указано
            if date:
                # Конвертация строки даты в объект datetime
                try:
                    # Конвертируем строку в дату
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    query = query.filter(Logs.timestamp >= date_obj).filter(
                        Logs.timestamp < date_obj + timedelta(days=1))
                except ValueError:
                    raise ValueError(
                        "Некорректный формат даты. Ожидается формат 'YYYY-MM-DD'.")

            total_count = query.count()  # Получаем общее количество записей
            # Получаем логи с учетом пагинации
            logs = query.offset(offset).limit(limit).all()

            # Форматируем логи в виде списка словарей
            result = [log.to_dict() for log in logs] if logs else []

            return result, total_count

        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка в сессии: {e}", extra={
                "login": "database"})
            raise
        finally:
            session.close()
            logger.debug(f"""Сессия закрыта""", extra={"login": "database"})
