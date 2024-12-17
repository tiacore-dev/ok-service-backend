from sqlalchemy import Column, String, UUID, Boolean
from app.database.db_setup import Base 
from sqlalchemy.orm import relationship
from uuid import uuid4


class WorkCategories(Base):
    __tablename__ = 'work_categories'

    work_category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    name = Column(String, nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)

        # Опционально, если хотите указать обратную связь
    work = relationship("Works", back_populates="work_category")

    def to_dict(self):
        return {
            "work_category_id": self.work_category_id,
            "name": self.name,
            "deleted": self.deleted
        }