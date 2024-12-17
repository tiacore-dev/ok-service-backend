from sqlalchemy import Column, Integer, String, UUID, ForeignKey, Boolean
from app.database.db_setup import Base 
from uuid import uuid4
from sqlalchemy.orm import relationship


class Works(Base):
    __tablename__ = 'works'
    
    work_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    name = Column(String, nullable=False)
    category = Column(UUID, ForeignKey('work_categories.work_category_id'), nullable=True)
    measurement_unit = Column(String, nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)
    
    work_category = relationship("WorkCategories", back_populates="work")
    work_price = relationship("WorkPrices", back_populates="work")
    project_work = relationship("ProjectWorks", back_populates="work")
    project_schedule = relationship("ProjectSchedules", back_populates="work")
    shift_report_details = relationship("ShiftreportDetails", back_populates="work")



    def to_dict(self):
        # Проверяем, есть ли роль
        #role_data = self.role_obj.to_dict() if self.role_obj else None
        return {
            "work_id": self.work_id,
            "name": self.name,
            "category": self.category if self.category else None,
            "measurement_unit": self.measurement_unit if self.measurement_unit else None,
            "deleted": self.deleted
        }
