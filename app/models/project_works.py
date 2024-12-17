from sqlalchemy import Column, UUID, ForeignKey, Boolean, Numeric
from app.database.db_setup import Base 
from uuid import uuid4
from sqlalchemy.orm import relationship


class ProjectWorks(Base):
    __tablename__ = 'project_works'
    
    project_work_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    work_id = Column(UUID, ForeignKey('works.work_id'), nullable=False)
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)
    summ = Column(Numeric(precision=10, scale=2), nullable=True)
    signed = Column(Boolean, nullable=False, default=False)
    
    work = relationship("Works", back_populates="project-work")


    def to_dict(self):
        # Проверяем, есть ли роль
        #role_data = self.role_obj.to_dict() if self.role_obj else None
        return {
            "project_work_id": self.project_id,
            "work_id": self.work_id,
            "quantity": self.quantity,
            "summ": self.summ if self.summ else None,
            "signed": self.signed
        }
