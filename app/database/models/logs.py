from app.database.db_setup import Base
from sqlalchemy import Column, String, DateTime, Text, UUID
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey
from uuid import uuid4

class Logs(Base):
    __tablename__ = 'logs'

    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    login = Column(String, nullable=False)  # Внешний ключ
    action = Column(String(255), nullable=False)  # Действие, которое было выполнено
    message = Column(Text, nullable=False)  # Сообщение лога
    timestamp = Column(DateTime, default=datetime.utcnow)  # Дата и время

    

    def to_dict(self):
        """Преобразование объекта лога в словарь."""
        return {
            "log_id": self.log_id,
            "login": self.login,
            "action": self.action,
            "message": self.message,
            "timestamp": self.timestamp.isoformat()  # Форматируем дату для JSON
        }
