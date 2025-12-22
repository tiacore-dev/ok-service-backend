from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Sequence,
    Float,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base

# Создаем SEQUENCE (он должен быть заранее в БД)
shift_reports_number_seq = Sequence("shift_reports_number_seq", start=1, increment=1)


class ShiftReports(Base):
    __tablename__ = "shift_reports"

    shift_report_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    user = Column(UUID, ForeignKey("users.user_id"), nullable=False)
    date = Column(BigInteger, nullable=False)
    date_start = Column(BigInteger, nullable=True)
    date_end = Column(BigInteger, nullable=True)
    project = Column(UUID, ForeignKey("projects.project_id"), nullable=False)
    lng_start = Column(Float, nullable=True)
    ltd_start = Column(Float, nullable=True)
    lng_end = Column(Float, nullable=True)
    ltd_end = Column(Float, nullable=True)
    distance_start = Column(Float, nullable=True)
    distance_end = Column(Float, nullable=True)
    signed = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        BigInteger,
        default=lambda: int(datetime.utcnow().timestamp()),
        server_default=text("EXTRACT(EPOCH FROM NOW())"),
        nullable=False,
    )
    created_by = Column(UUID, ForeignKey("users.user_id"), nullable=False)
    night_shift = Column(Boolean, nullable=False, default=False)
    extreme_conditions = Column(Boolean, nullable=False, default=False)
    deleted = Column(Boolean, nullable=False, default=False)
    number = Column(
        Integer,
        shift_reports_number_seq,
        server_default=shift_reports_number_seq.next_value(),
        unique=True,
        nullable=False,
    )

    projects = relationship("Projects", back_populates="shift_report")
    shift_report_details = relationship(
        "ShiftReportDetails", back_populates="shift_reports", cascade="all, delete"
    )

    shift_report_creator = relationship(
        "Users", back_populates="created_shift_reports", foreign_keys=[created_by]
    )
    users = relationship("Users", back_populates="shift_report", foreign_keys=[user])

    def __repr__(self):
        return (
            f"<ShiftReports(shift_report_id={self.shift_report_id}, user={self.user}, "
            f"date={self.date}, project={self.project}, signed={self.signed}, "
            f"deleted={self.deleted}, number={self.number}, "
            f"lng_start={self.lng_start}, ltd_start={self.ltd_start}, "
            f"lng_end={self.lng_end}, ltd_end={self.ltd_end}, "
            f"distance_start={self.distance_start}, distance_end={self.distance_end}, "
            f"date_start={self.date_start}, date_end={self.date_end})>"
        )

    def to_dict(self):
        return {
            "shift_report_id": str(self.shift_report_id),
            "user": str(self.user),
            "date": self.date,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "project": str(self.project),
            "lng_start": self.lng_start,
            "ltd_start": self.ltd_start,
            "lng_end": self.lng_end,
            "ltd_end": self.ltd_end,
            "distance_start": self.distance_start,
            "distance_end": self.distance_end,
            "signed": self.signed,
            "deleted": self.deleted,
            "created_by": str(self.created_by),
            "created_at": self.created_at,
            "night_shift": self.night_shift,
            "extreme_conditions": self.extreme_conditions,
            "number": self.number,
        }
