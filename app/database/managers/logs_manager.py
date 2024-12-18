from app.database.models.logs import Logs
from app.database.db_globals import Session
from datetime import timedelta, datetime

class LogManager():
    def __init__(self):
        self.Session = Session

    def add_logs(self, login, action, message):
        """Добавление лога."""
        session = self.Session()
        new_record = Logs(login=login, action=action, message=message)  # Создаем объект Logs
        session.add(new_record)  # Добавляем новый лог через сессию
        session.commit()  # Не забудьте зафиксировать изменения в базе данных
        return new_record

    def get_logs_by_date(self, date, offset=0, limit=10):
        """Получение логов по дате."""
        session = self.Session()
        return session.query(Logs).filter(Logs.timestamp >= date, Logs.timestamp < date + timedelta(days=1)).offset(offset).limit(limit).all()

    def filter_by_date(self, user_id=None, date=None, offset=0, limit=10):
        """Фильтрация логов по дате и ID пользователя."""
        session = self.Session()
        query = session.query(Logs)
        if user_id:
            query = query.filter(Logs.user_id == user_id)
        if date:
            date_obj = datetime.strptime(date, '%Y-%m-%d')  # Конвертация строки даты в объект datetime
            query = query.filter(Logs.timestamp >= date_obj, Logs.timestamp < date_obj + timedelta(days=1))
        return query.offset(offset).limit(limit).all()
    
    def get_logs(self, user_id=None, date=None, offset=0, limit=10):
        """Получение логов с фильтрацией и пагинацией."""
        session = self.Session()
        query = session.query(Logs)

        # Фильтрация по user_id, если указано
        if user_id:
            query = query.filter(Logs.user_id == user_id)

        # Фильтрация по дате, если указано
        if date:
            # Конвертация строки даты в объект datetime
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d')  # Конвертируем строку в дату
                query = query.filter(Logs.timestamp >= date_obj).filter(Logs.timestamp < date_obj + timedelta(days=1))
            except ValueError:
                raise ValueError("Некорректный формат даты. Ожидается формат 'YYYY-MM-DD'.")

        total_count = query.count()  # Получаем общее количество записей
        logs = query.offset(offset).limit(limit).all()  # Получаем логи с учетом пагинации

        # Форматируем логи в виде списка словарей
        result = [log.to_dict() for log in logs] if logs else []

        return result, total_count
