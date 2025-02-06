from uuid import uuid4
from datetime import datetime
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, UUID, ForeignKey, Boolean, Integer
from app.database.db_setup import Base


class Works(Base):
    __tablename__ = 'works'

    work_id = Column(UUID(as_uuid=True), primary_key=True,
                     default=uuid4, nullable=False)
    name = Column(String, nullable=False)
    category = Column(UUID, ForeignKey(
        'work_categories.work_category_id'), nullable=True)
    measurement_unit = Column(String, nullable=True)
    created_at = Column(Integer, default=lambda: int(datetime.utcnow().timestamp()),
                        server_default=text("EXTRACT(EPOCH FROM NOW())"), nullable=False)
    created_by = Column(UUID, ForeignKey(
        'users.user_id'), nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)

    work_category = relationship(
        "WorkCategories", back_populates="works", lazy="joined")
    work_price = relationship("WorkPrices", back_populates="works")
    project_work = relationship("ProjectWorks", back_populates="works")
    project_schedule = relationship("ProjectSchedules", back_populates="works")
    shift_report_details = relationship(
        "ShiftReportDetails", back_populates="works")

    work_creator = relationship("Users", back_populates="created_works")

    def __repr__(self):
        return (f"<Works(work_id={self.work_id}, name={self.name}, category={self.category}, "
                f"measurement_unit={self.measurement_unit}, deleted={self.deleted})>")

    def to_dict(self):
        return {
            "work_id": str(self.work_id),
            "name": self.name,
            "category": self.work_category.to_dict() if self.work_category else None,
            "measurement_unit": self.measurement_unit,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "deleted": self.deleted
        }
