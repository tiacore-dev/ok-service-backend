from uuid import uuid4

from sqlalchemy import UUID, Boolean, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database.db_setup import Base


class Places(Base):
    __tablename__ = "places"

    place_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    object_id = Column(
        UUID(as_uuid=True),
        ForeignKey("objects.object_id"),
        nullable=False,
    )
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)

    object = relationship("Objects", back_populates="places")

    def to_dict(self):
        return {
            "place_id": str(self.place_id),
            "object_id": str(self.object_id),
            "name": self.name,
            "description": self.description,
            "deleted": self.deleted,
        }
