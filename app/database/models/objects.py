from uuid import uuid4
from datetime import datetime
from sqlalchemy.sql import text

from sqlalchemy import Column, String, ForeignKey, Boolean, UUID, Integer
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
    manager = Column(UUID, ForeignKey('users.user_id'), nullable=True)
    created_at = Column(Integer, default=lambda: int(datetime.utcnow(
    ).timestamp()), server_default=text("EXTRACT(EPOCH FROM NOW())"))
    created_by = Column(UUID(as_uuid=True), ForeignKey(
        'users.user_id'), nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)

    # Определяем отношение к объекту ObjectStatuses
    object_status = relationship("ObjectStatuses", back_populates="object")
    project = relationship("Projects", back_populates="objects")

    object_manager = relationship(
        "Users", back_populates="managed_objects", foreign_keys=[manager])
    object_creator = relationship(
        "Users", back_populates="created_objects", foreign_keys=[created_by])

    def __repr__(self):
        return (f"<Objects(object_id={self.object_id}, name={self.name}, "
                f"address={self.address}, description={self.description}, "
                f"status={self.status}, manager={self.manager}, deleted={self.deleted})>")

    def to_dict(self):
        return {
            "object_id": str(self.object_id),
            "name": self.name,
            "address": self.address if self.address else None,
            "description": self.description if self.description else None,
            "status": self.status,
            "manager": str(self.manager),
            "created_at": self.created_at,
            "created_by": self.created_by,
            "deleted": self.deleted
        }
