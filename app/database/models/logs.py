from uuid import uuid4

from sqlalchemy import Column, DateTime, String, Text, UUID

from app.database.db_setup import Base
from app.database.time_utils import utc_now


class Logs(Base):
    __tablename__ = 'logs'

    log_id = Column(UUID(as_uuid=True), primary_key=True,
                    default=uuid4, nullable=False)
    login = Column(String, nullable=False)  # Внешний ключ
    # Действие, которое было выполнено
    action = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)  # Сообщение лога
    timestamp = Column(DateTime(timezone=True), default=utc_now)  # Дата и время

    def __repr__(self):
        return f"<Logs(log_id={self.log_id}, login={self.login}, action={self.action}, timestamp={self.timestamp})>"

    def to_dict(self):
        """Преобразование объекта лога в словарь."""
        return {
            "log_id": self.log_id,
            "login": self.login,
            "action": self.action,
            "message": self.message,
            "timestamp": self.timestamp.isoformat()  # Форматируем дату для JSON
        }
