from sqlalchemy import Column, String
from app.database.db_setup import Base
from sqlalchemy.orm import relationship


class ObjectStatuses(Base):
    __tablename__ = 'object_statuses'

    object_status_id = Column(String, primary_key=True, nullable=False)
    name = Column(String, nullable=False)

    # Опционально, если хотите указать обратную связь
    object = relationship("Objects", back_populates="object_status")

    def to_dict(self):
        return {
            "object_status_id": self.object_status_id,
            "name": self.name
        }
