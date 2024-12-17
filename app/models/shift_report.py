from sqlalchemy import Column, Integer, String, UUID, ForeignKey, Boolean, Numeric
from app.database.db_setup import Base 
from uuid import uuid4
from sqlalchemy.orm import relationship


class ShiftReports(Base):
    __tablename__ = 'shift_reports'
    
    shift_report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    user_id = Column(UUID, ForeignKey('users.user_id'), nullable=False)
    date = Column(Integer, nullable=False)
    project_id = Column(UUID, ForeignKey('projects.project_id'), nullable=False)
    signed = Column(Boolean, nullable=False, default=False)
    deleted = Column(Boolean, nullable=False, default=False)
    
    user = relationship("Users", back_populates="shif_report")
    project = relationship("Projects", back_populates="shift_report")
    shift_report_details = relationship("ShiftreportDetails", back_populates="shift_report")


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
