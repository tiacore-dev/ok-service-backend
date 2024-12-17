from sqlalchemy import Column, String, ForeignKey, Boolean
from app.database.db_setup import Base 
from sqlalchemy.orm import relationship


class Objects(Base):
    __tablename__ = 'objects'

    object_id = Column(String, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    description = Column(String, nullable=True)
    status = Column(String, ForeignKey('object_statuses.object_status_id'), nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)

        # Определяем отношение к объекту ObjectStatuses
    object_status = relationship("ObjectStatuses", back_populates="object")
    project = relationship("Projects", back_populates="object")


    def to_dict(self):
        return {
            "object_id": self.object_id,
            "name": self.name,
            "address": self.address if self.address else None,
            "description": self.description if self.description else None,
            "status": self.status if self.status else None,
            "deleted": self.deleted
        }
