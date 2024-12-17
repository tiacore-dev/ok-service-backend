from contextlib import contextmanager
from abc import ABC, abstractmethod
from app.database.db_globals import Session
from sqlalchemy import inspect

class BaseDBManager(ABC):
    @property
    @abstractmethod
    def model(self):
        """Метод, который возвращает модель (таблицу) для работы."""
        pass

    @contextmanager
    def session_scope(self):
        """Контекстный менеджер для управления сессией."""
        session = Session()  # Создаем экземпляр сессии
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    def add(self, **kwargs):
        """Добавление записи в базу данных."""
        with self.session_scope() as session:
            new_record = self.model(**kwargs)
            session.add(new_record)
            return new_record

    def get_by_id(self, record_id):
        """Получение записи по ID (по первичному ключу)."""
        with self.session_scope() as session:
            primary_key = inspect(self.model).primary_key
            if not primary_key:
                raise ValueError(f"No primary key found for model {self.model.__name__}")

            primary_key_name = primary_key[0].name
            
            # Создаем фильтр по первичному ключу
            record = session.query(self.model).filter(getattr(self.model, primary_key_name) == record_id).first()

            if record:
                return record.to_dict()  # Возвращаем сразу словарь, а не объект
            return None

    def get_record_by_id(self, record_id):
        """Получение записи по ID в виде объекта."""
        with self.session_scope() as session:
            primary_key = inspect(self.model).primary_key
            if not primary_key:
                raise ValueError(f"No primary key found for model {self.model.__name__}")

            primary_key_name = primary_key[0].name
            record = session.query(self.model).filter(getattr(self.model, primary_key_name) == record_id).first()
            if record:
                return record
            return None

    def get_all(self, offset=0, limit=None):
        """Получение всех записей с поддержкой пагинации."""
        with self.session_scope() as session:
            records = session.query(self.model).offset(offset).limit(limit).all()
            return [record.to_dict() for record in records]  # Преобразуем записи в словари
        
    def get_count(self):
        """Получение общего количества записей."""
        with self.session_scope() as session:
            return session.query(self.model).count()


    def update(self, record_id, **kwargs):
        """Обновление записи по ID."""
        with self.session_scope() as session:
            record = self.get_by_id(record_id)
            if record:
                for key, value in kwargs.items():
                    setattr(record, key, value)
                session.commit()
            return record

    def delete(self, record_id):
        """Удаление записи по ID."""
        with self.session_scope() as session:
            record = self.get_record_by_id(record_id)
            if record:
                session.delete(record)
                session.commit()
            return record

    def filter_by(self, **kwargs):
        """Фильтрация записей по заданным критериям."""
        with self.session_scope() as session:
            return session.query(self.model).filter_by(**kwargs).all()
        
    def filter_by_dict(self, **kwargs):
        """Фильтрация записей с преобразованием объектов в словари."""
        with self.session_scope() as session:
            records = session.query(self.model).filter_by(**kwargs).all()
            return [record.to_dict() for record in records]


    def filter_one_by_dict(self, **kwargs):
        """Фильтрация записей с ожиданием одного результата, возвращаем словарь или None."""
        with self.session_scope() as session:
            record = session.query(self.model).filter_by(**kwargs).first()
            return record.to_dict() if record else None

    def exists_by_id(self, record_id):
        with self.session_scope() as session:
            primary_key = inspect(self.model).primary_key
            if not primary_key:
                raise ValueError(f"No primary key found for model {self.model.__name__}")

            primary_key_name = primary_key[0].name
            return session.query(self.model).filter(getattr(self.model, primary_key_name) == record_id).count() > 0

    def exists(self, **kwargs):
        """Проверяет существование записи с указанными полями."""
        with self.session_scope() as session:
            return session.query(self.model).filter_by(**kwargs).count() > 0
