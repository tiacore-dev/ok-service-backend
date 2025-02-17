from uuid import uuid4
from datetime import datetime
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, UUID, Boolean, BigInteger, ForeignKey
from app.database.db_setup import Base


class WorkCategories(Base):
    __tablename__ = 'work_categories'

    work_category_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()),
                        server_default=text("EXTRACT(EPOCH FROM NOW())"), nullable=False)
    created_by = Column(UUID, ForeignKey(
        'users.user_id'), nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)

    # Опционально, если хотите указать обратную связь
    works = relationship("Works", back_populates="work_category")

    work_category_creator = relationship(
        "Users", back_populates="created_work_categories")

    def __repr__(self):
        return (f"<WorkCategories(work_category_id={self.work_category_id}, "
                f"name={self.name}, deleted={self.deleted})>")

    def to_dict(self):
        return {
            "work_category_id": str(self.work_category_id),
            "name": self.name,
            "created_by": str(self.created_by),
            "created_at": self.created_at,
            "deleted": self.deleted
        }
