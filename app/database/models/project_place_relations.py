from uuid import uuid4

from sqlalchemy import UUID, Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.db_setup import Base


class ProjectPlaceRelations(Base):
    __tablename__ = "project_place_relations"
    __table_args__ = (
        UniqueConstraint("project_id", "place_id", name="uq_project_place_relations"),
    )

    project_place_relation_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id"), nullable=False)
    place_id = Column(UUID(as_uuid=True), ForeignKey("places.place_id"), nullable=False)

    project = relationship("Projects", back_populates="project_place_relations")
    place = relationship("Places", back_populates="project_place_relations")

    def to_dict(self):
        return {
            "project_place_relation_id": str(self.project_place_relation_id),
            "project_id": str(self.project_id),
            "place_id": str(self.place_id),
        }
