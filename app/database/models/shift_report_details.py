from uuid import uuid4
from datetime import datetime
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from sqlalchemy import Column, UUID, ForeignKey, Numeric, BigInteger
from app.database.db_setup import Base


class ShiftReportDetails(Base):
    __tablename__ = 'shift_report_details'

    shift_report_detail_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    shift_report = Column(UUID, ForeignKey(
        'shift_reports.shift_report_id', ondelete='CASCADE'), nullable=False)
    project_work = Column(UUID, ForeignKey(
        'project_works.project_work_id'), nullable=True)
    work = Column(UUID, ForeignKey('works.work_id'), nullable=False)
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)
    summ = Column(Numeric(precision=10, scale=2), nullable=False)
    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()),
                        server_default=text("EXTRACT(EPOCH FROM NOW())"), nullable=False)
    created_by = Column(UUID, ForeignKey(
        'users.user_id'), nullable=False)

    shift_reports = relationship(
        "ShiftReports", back_populates="shift_report_details")
    works = relationship("Works", back_populates="shift_report_details")

    shift_report_details_creator = relationship(
        "Users", back_populates="created_shift_report_details")

    project_works = relationship(
        "ProjectWorks", back_populates="shift_report_details")

    def __repr__(self):
        return (f"<ShiftReportDetails(shift_report_detail_id={self.shift_report_detail_id}, "
                f"shift_report={self.shift_report},  "
                f"quantity={self.quantity}, summ={self.summ})>")

    def to_dict(self):
        return {
            "shift_report_detail_id": str(self.shift_report_detail_id),
            "project_work": str(self.project_work) if self.project_work else None,
            "project_work_name": self.project_works.project_work_name if self.project_works else None,
            "shift_report": str(self.shift_report),
            "work": str(self.work),
            "quantity": self.quantity,
            "created_by": str(self.created_by),
            "created_at": self.created_at,
            "summ": self.summ
        }
