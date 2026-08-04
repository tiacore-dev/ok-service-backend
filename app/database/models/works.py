from uuid import uuid4

from sqlalchemy import UUID, BigInteger, Boolean, Column, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_seconds


class Works(Base):
    __tablename__ = "works"

    work_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    name = Column(String, nullable=False)
    category = Column(
        UUID, ForeignKey("work_categories.work_category_id"), nullable=True
    )
    measurement_unit = Column(
        UUID(as_uuid=True), ForeignKey("measurement_units.measurement_unit_id"), nullable=True
    )
    created_at = Column(
        BigInteger,
        default=utc_epoch_seconds,
        server_default=text("EXTRACT(EPOCH FROM NOW())"),
        nullable=False,
    )
    created_by = Column(UUID, ForeignKey("users.user_id"), nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)

    work_category = relationship(
        "WorkCategories", back_populates="works", lazy="joined"
    )
    measurement_unit_ref = relationship(
        "MeasurementUnits", back_populates="works", lazy="joined"
    )
    work_price = relationship("WorkPrices", back_populates="works")
    project_work = relationship("ProjectWorks", back_populates="works")
    project_schedule = relationship("ProjectSchedules", back_populates="works")
    shift_report_details = relationship("ShiftReportDetails", back_populates="works")
    material_works = relationship("WorkMaterialRelations", back_populates="works")

    work_creator = relationship("Users", back_populates="created_works")

    def __repr__(self):
        return (
            f"<Works(work_id={self.work_id}, name={self.name}, category={
                self.category
            }, "
            f"measurement_unit={self.measurement_unit}, deleted={self.deleted})>"
        )

    def to_dict(self):
        return {
            "work_id": str(self.work_id),
            "name": self.name,
            "category": self.work_category.to_dict() if self.work_category else None,
            "measurement_unit": self.measurement_unit_ref.to_dict()
            if self.measurement_unit_ref
            else None,
            "created_by": str(self.created_by),
            "created_at": self.created_at,
            "deleted": self.deleted,
            "work_prices": [price.to_dict() for price in self.work_price],
        }
