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

    def __repr__(self):
        return (f"<ProjectSchedules(project_schedule_id={self.project_schedule_id}, "
                f"work={self.work}, quantity={self.quantity}, date={self.date})>")

    def to_dict(self):
        return {
            "project_schedule_id": str(self.project_schedule_id),
            "work": self.work,
            "quantity": self.quantity,
            "date": self.date
        }
