from uuid import uuid4
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer,  UUID, ForeignKey, Numeric
from app.database.db_setup import Base


class ProjectSchedules(Base):
    __tablename__ = 'project_schedules'

    project_schedule_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    work = Column(UUID, ForeignKey('works.work_id'), nullable=False)
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)
    date = Column(Integer, nullable=True)

    works = relationship("Works", back_populates="project_schedule")

    def to_dict(self):
        # Проверяем, есть ли роль
        work_data = self.works.to_dict() if self.works else str(self.work)
        return {
            "project_schedule_id": str(self.project_schedule_id),
            "work": work_data,
            "quantity": self.quantity,
            "date": self.date
        }
