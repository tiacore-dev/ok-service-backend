from uuid import uuid4

from sqlalchemy import UUID, Column, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.db_setup import Base


class ShiftPlaceRelations(Base):
    __tablename__ = "shift_place_relations"
    __table_args__ = (
        UniqueConstraint(
            "shift_report_id", "place_id", name="uq_shift_place_relations"
        ),
    )

    shift_place_relation_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    shift_report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shift_reports.shift_report_id", ondelete="CASCADE"),
        nullable=False,
    )
    place_id = Column(UUID(as_uuid=True), ForeignKey("places.place_id"), nullable=False)
    comment = Column(Text, nullable=True)

    shift_report = relationship("ShiftReports", back_populates="shift_place_relations")
    place = relationship("Places", back_populates="shift_place_relations")

    def to_dict(self):
        return {
            "shift_place_relation_id": str(self.shift_place_relation_id),
            "shift_report_id": str(self.shift_report_id),
            "place_id": str(self.place_id),
            "comment": self.comment,
        }
