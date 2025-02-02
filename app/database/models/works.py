from uuid import uuid4
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, UUID, ForeignKey, Boolean
from app.database.db_setup import Base


class Works(Base):
    __tablename__ = 'works'

    work_id = Column(UUID(as_uuid=True), primary_key=True,
                     default=uuid4, nullable=False)
    name = Column(String, nullable=False)
    category = Column(UUID, ForeignKey(
        'work_categories.work_category_id'), nullable=True)
    measurement_unit = Column(String, nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)

    work_category = relationship("WorkCategories", back_populates="works")
    work_price = relationship("WorkPrices", back_populates="works")
    project_work = relationship("ProjectWorks", back_populates="works")
    project_schedule = relationship("ProjectSchedules", back_populates="works")
    shift_report_details = relationship(
        "ShiftReportDetails", back_populates="works")

    def to_dict(self):
        return {
            "work_id": str(self.work_id),
            "name": self.name,
            # ❗ Без `json.dumps()`
            "category": self.work_category.to_dict() if self.work_category else None,
            "measurement_unit": self.measurement_unit,
            "deleted": self.deleted
        }
