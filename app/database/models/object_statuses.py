from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.database.db_setup import Base


class ObjectStatuses(Base):
    __tablename__ = 'object_statuses'

    object_status_id = Column(String, primary_key=True, nullable=False)
    name = Column(String, nullable=False)

    # Опционально, если хотите указать обратную связь
    object = relationship("Objects", back_populates="object_status")

    def __repr__(self):
        return f"<ObjectStatuses(object_status_id={self.object_status_id}, name={self.name})>"

    def to_dict(self):
        return {
            "object_status_id": self.object_status_id,
            "name": self.name
        }
