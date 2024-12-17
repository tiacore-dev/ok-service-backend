from sqlalchemy import Column, UUID, ForeignKey, Numeric
from app.database.db_setup import Base 
from uuid import uuid4
from sqlalchemy.orm import relationship


class ShiftReportDetails(Base):
    __tablename__ = 'shift_report_details'
    
    shift_report_details_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    shift_report_id = Column(UUID, ForeignKey('shift_reports.shift_report_id'), nullable=False)
    work_id = Column(UUID, ForeignKey('works.work_id'), nullable=False)
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)
    summ = Column(Numeric(precision=10, scale=2), nullable=False)
    
    shift_report = relationship("ShiftReports", back_populates="shift_report_details")
    work = relationship("Works", back_populates="shift_report_details")


    def to_dict(self):
        # Проверяем, есть ли роль
        #role_data = self.role_obj.to_dict() if self.role_obj else None
        return {
            "shift_report_id": self.shift_report_id,
            "user_id": self.user_id,
            "date": self.date,
            "project_id": self.project_id,
            "signed": self.signed,
            "deleted": self.deleted
        }
