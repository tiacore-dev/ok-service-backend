from uuid import uuid4
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, UUID, ForeignKey, Boolean
from app.database.db_setup import Base


class ShiftReports(Base):
    __tablename__ = 'shift_reports'

    shift_report_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    user = Column(UUID, ForeignKey('users.user_id'), nullable=False)
    date = Column(Integer, nullable=False)
    project = Column(UUID, ForeignKey('projects.project_id'), nullable=False)
    signed = Column(Boolean, nullable=False, default=False)
    deleted = Column(Boolean, nullable=False, default=False)

    users = relationship("Users", back_populates="shift_report")
    projects = relationship("Projects", back_populates="shift_report")
    shift_report_details = relationship(
        "ShiftReportDetails", back_populates="shift_reports")

    def to_dict(self):
        # Проверяем, есть ли роль
        user_data = self.users.to_dict() if self.users else str(self.user)
        project_data = self.projects.to_dict() if self.projects else str(self.project)
        return {
            "shift_report_id": str(self.shift_report_id),
            "user": user_data,
            "date": self.date,
            "project": project_data,
            "signed": self.signed,
            "deleted": self.deleted
        }
