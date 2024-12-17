from sqlalchemy import Column, Integer,  UUID, ForeignKey, Numeric
from app.database.db_setup import Base 
from uuid import uuid4
from sqlalchemy.orm import relationship


class ProjectSchedules(Base):
    __tablename__ = 'project_schedules'
    
    project_schedule_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    work_id = Column(UUID, ForeignKey('works.work_id'), nullable=False)
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)
    date = Column(Integer, nullable=True)

    work = relationship("Works", back_populates="project_schedule")


    def to_dict(self):
        # Проверяем, есть ли роль
        #role_data = self.role_obj.to_dict() if self.role_obj else None
        return {
            "project_schedule_id": self.project_schedule_id,
            "work_id": self.work_id,
            "quantity": self.quantity,
            "date": self.date
        }
