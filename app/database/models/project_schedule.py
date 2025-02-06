from uuid import uuid4
from datetime import datetime
from sqlalchemy.sql import text
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
    created_at = Column(Integer, default=lambda: int(datetime.utcnow().timestamp()),
                        server_default=text("EXTRACT(EPOCH FROM NOW())"), nullable=False)
    created_by = Column(UUID, ForeignKey(
        'users.user_id'), nullable=False)

    works = relationship("Works", back_populates="project_schedule")
    project_schedule_creator = relationship(
        "Users", back_populates="created_project_schedules")

    def __repr__(self):
        return (f"<ProjectSchedules(project_schedule_id={self.project_schedule_id}, "
                f"work={self.work}, quantity={self.quantity}, date={self.date})>")

    def to_dict(self):
        return {
            "project_schedule_id": str(self.project_schedule_id),
            "work": self.work,
            "quantity": self.quantity,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "date": self.date
        }
