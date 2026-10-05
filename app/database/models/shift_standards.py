from uuid import uuid4

from sqlalchemy import BigInteger, CheckConstraint, Column, Float, ForeignKey, Integer, Text, UUID
from sqlalchemy.sql import text

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_milliseconds


class ShiftStandards(Base):
    __tablename__ = "shift_standards"
    __table_args__ = (
        CheckConstraint("standard > 0", name="check_shift_standards_standard_positive"),
    )

    shift_standard_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    category = Column(Integer, nullable=False, unique=True)
    standard = Column(Float, nullable=False)
    notification_text = Column(Text, nullable=True)
    created_at = Column(
        BigInteger,
        default=utc_epoch_milliseconds,
        server_default=text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
        nullable=False,
    )
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)

    def to_dict(self):
        return {
            "shift_standard_id": str(self.shift_standard_id),
            "category": self.category,
            "standard": self.standard,
            "notification_text": self.notification_text,
            "created_at": self.created_at,
            "created_by": str(self.created_by),
        }
