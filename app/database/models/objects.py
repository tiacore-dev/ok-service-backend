from uuid import uuid4
from sqlalchemy import Column, String, ForeignKey, Boolean, UUID
from sqlalchemy.orm import relationship
from app.database.db_setup import Base


class Objects(Base):
    __tablename__ = 'objects'

    object_id = Column(UUID(as_uuid=True), primary_key=True,
                       default=uuid4, nullable=False)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    description = Column(String, nullable=True)
    status = Column(String, ForeignKey(
        'object_statuses.object_status_id'), nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)

    # Определяем отношение к объекту ObjectStatuses
    object_status = relationship("ObjectStatuses", back_populates="object")
    project = relationship("Projects", back_populates="objects")

    def __repr__(self):
        return (f"<Objects(object_id={self.object_id}, name={self.name}, "
                f"address={self.address}, description={self.description}, "
                f"status={self.status}, deleted={self.deleted})>")

    def to_dict(self):
        return {
            "object_id": str(self.object_id),
            "name": self.name,
            "address": self.address if self.address else None,
            "description": self.description if self.description else None,
            "status": self.status,
            "deleted": self.deleted
        }
