from uuid import uuid4
from sqlalchemy.orm import relationship
from sqlalchemy import Column, UUID, ForeignKey, Numeric
from app.database.db_setup import Base


class ShiftReportDetails(Base):
    __tablename__ = 'shift_report_details'

    shift_report_detail_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    shift_report = Column(UUID, ForeignKey(
        'shift_reports.shift_report_id'), nullable=False)
    work = Column(UUID, ForeignKey('works.work_id'), nullable=False)
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)
    summ = Column(Numeric(precision=10, scale=2), nullable=False)

    shift_reports = relationship(
        "ShiftReports", back_populates="shift_report_details")
    works = relationship("Works", back_populates="shift_report_details")

    def to_dict(self):
        # Проверяем, есть ли роль
        # shift_report_data = self.shift_reports.to_dict(
        # ) if self.shift_reports else str(self.shift_report)
        # work_data = self.works.to_dict() if self.works else str(self.work)
        return {
            "shift_report_detail_id": str(self.shift_report_detail_id),
            "shift_report": self.shift_report,
            "work": self.work,
            "quantity": self.quantity,
            "summ": self.summ
        }
