
from uuid import uuid4
from datetime import datetime
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, UUID, ForeignKey, Boolean, BigInteger, Sequence
from app.database.db_setup import Base

# Создаем SEQUENCE (он должен быть заранее в БД)
shift_reports_number_seq = Sequence(
    "shift_reports_number_seq", start=1, increment=1)


class ShiftReports(Base):
    __tablename__ = 'shift_reports'

    shift_report_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    user = Column(UUID, ForeignKey('users.user_id'), nullable=False)
    date = Column(BigInteger, nullable=False)
    project = Column(UUID, ForeignKey('projects.project_id'), nullable=False)
    signed = Column(Boolean, nullable=False, default=False)
    created_at = Column(Integer, default=lambda: int(datetime.utcnow().timestamp()),
                        server_default=text("EXTRACT(EPOCH FROM NOW())"), nullable=False)
    created_by = Column(UUID, ForeignKey(
        'users.user_id'), nullable=False)
    night_shift = Column(Boolean, nullable=False, default=False)
    extreme_conditions = Column(Boolean, nullable=False, default=False)
    deleted = Column(Boolean, nullable=False, default=False)
    number = Column(Integer, shift_reports_number_seq,
                    server_default=shift_reports_number_seq.next_value(), unique=True, nullable=False)

    projects = relationship("Projects", back_populates="shift_report")
    shift_report_details = relationship(
        "ShiftReportDetails", back_populates="shift_reports")

    shift_report_creator = relationship(
        "Users", back_populates="created_shift_reports", foreign_keys=[created_by])
    users = relationship(
        "Users", back_populates="shift_report", foreign_keys=[user])

    def __repr__(self):
        return (f"<ShiftReports(shift_report_id={self.shift_report_id}, user={self.user}, "
                f"date={self.date}, project={
                    self.project}, signed={self.signed}, "
                f"deleted={self.deleted}, number={self.number})>")

    def to_dict(self):
        return {
            "shift_report_id": str(self.shift_report_id),
            "user": str(self.user),
            "date": self.date,
            "project": str(self.project),
            "signed": self.signed,
            "deleted": self.deleted,
            "created_by": str(self.created_by),
            "created_at": self.created_at,
            "night_shift": self.night_shift,
            "extreme_confitions": self.extreme_conditions,
            "number": self.number
        }
