from datetime import datetime
from uuid import uuid4

from sqlalchemy import UUID, BigInteger, Column, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base


class ShiftReportMaterials(Base):
    __tablename__ = "shift_report_materials"

    shift_report_material_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    shift_report = Column(
        UUID,
        ForeignKey("shift_reports.shift_report_id", ondelete="CASCADE"),
        nullable=False,
    )
    material = Column(
        UUID, ForeignKey("materials.material_id", ondelete="CASCADE"), nullable=False
    )
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)
    shift_report_detail = Column(
        UUID, ForeignKey("shift_report_details.shift_report_detail_id"), nullable=True
    )
    created_at = Column(
        BigInteger,
        default=lambda: int(datetime.utcnow().timestamp()),
        server_default=text("EXTRACT(EPOCH FROM NOW())"),
        nullable=False,
    )
    created_by = Column(UUID, ForeignKey("users.user_id"), nullable=False)

    shift_reports = relationship(
        "ShiftReports", back_populates="shift_report_materials"
    )
    materials = relationship("Materials", back_populates="shift_report_materials")
    shift_report_details = relationship(
        "ShiftReportDetails", back_populates="shift_report_materials"
    )

    shift_report_material_creator = relationship(
        "Users", back_populates="created_shift_report_materials"
    )

    def __repr__(self):
        return f"<ShiftReportMaterials(shift_report_material_id={
            self.shift_report_material_id
        })>"

    def to_dict(self):
        return {
            "shift_report_material_id": str(self.shift_report_material_id),
            "shift_report": str(self.shift_report),
            "material": str(self.material),
            "quantity": self.quantity,
            "shift_report_detail": str(self.shift_report_detail)
            if self.shift_report_detail  # type: ignore
            else None,  # type: ignore
            "created_by": str(self.created_by),
            "created_at": self.created_at,
        }
