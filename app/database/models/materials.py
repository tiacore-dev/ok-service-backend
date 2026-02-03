from datetime import datetime
from uuid import uuid4

from sqlalchemy import UUID, BigInteger, Boolean, Column, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base


class Materials(Base):
    __tablename__ = "materials"

    material_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    name = Column(String, nullable=False)
    measurement_unit = Column(String, nullable=True)

    created_at = Column(
        BigInteger,
        default=lambda: int(datetime.utcnow().timestamp()),
        server_default=text("EXTRACT(EPOCH FROM NOW())"),
    )
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)
    material_creator = relationship(
        "Users", back_populates="created_materials", foreign_keys=[created_by]
    )

    def __repr__(self):
        return f"<Materials(material_id={self.material_id}, name={self.name}, "

    def to_dict(self):
        return {
            "material_id": str(self.material_id),
            "name": self.name,
            "measurement_unit": self.measurement_unit,
            "created_at": self.created_at,
            "created_by": str(self.created_by),
            "deleted": self.deleted,
        }
