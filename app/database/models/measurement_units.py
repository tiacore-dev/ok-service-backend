from uuid import uuid4

from sqlalchemy import UUID, BigInteger, Column, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_seconds


class MeasurementUnits(Base):
    __tablename__ = "measurement_units"

    measurement_unit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(
        BigInteger,
        default=utc_epoch_seconds,
        server_default=text("EXTRACT(EPOCH FROM NOW())"),
        nullable=False,
    )
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)

    works = relationship("Works", back_populates="measurement_unit_ref")
    materials = relationship("Materials", back_populates="measurement_unit_ref")

    def to_dict(self):
        return {
            "measurement_unit_id": str(self.measurement_unit_id),
            "name": self.name,
            "created_at": self.created_at,
            "created_by": str(self.created_by) if self.created_by is not None else None,
        }
