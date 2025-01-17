from uuid import uuid4
from sqlalchemy.orm import relationship
from sqlalchemy import Column, UUID, ForeignKey, Boolean, Numeric
from app.database.db_setup import Base


class ProjectWorks(Base):
    __tablename__ = 'project_works'

    project_work_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    work = Column(UUID, ForeignKey('works.work_id'), nullable=False)
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)
    summ = Column(Numeric(precision=10, scale=2), nullable=True)
    signed = Column(Boolean, nullable=False, default=False)

    works = relationship("Works", back_populates="project_work")

    def to_dict(self):
        # Проверяем, есть ли роль
        # work_data = self.works.to_dict() if self.works else str(self.work)
        return {
            "project_work_id": str(self.project_work_id),
            "work": self.work,
            "quantity": self.quantity,
            "summ": self.summ if self.summ else None,
            "signed": self.signed
        }
