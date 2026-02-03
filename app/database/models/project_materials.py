from datetime import datetime
from uuid import uuid4

from sqlalchemy import UUID, BigInteger, Column, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base


class ProjectMaterials(Base):
    __tablename__ = "project_materials"

    project_material_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    project = Column(
        UUID, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False
    )
    material = Column(
        UUID, ForeignKey("materials.material_id", ondelete="CASCADE"), nullable=False
    )
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)
    project_work = Column(
        UUID, ForeignKey("project_works.project_work_id"), nullable=True
    )
    created_at = Column(
        BigInteger,
        default=lambda: int(datetime.utcnow().timestamp()),
        server_default=text("EXTRACT(EPOCH FROM NOW())"),
        nullable=False,
    )
    created_by = Column(UUID, ForeignKey("users.user_id"), nullable=False)

    projects = relationship("Projects", back_populates="project_materials")
    materials = relationship("Materials", back_populates="project_materials")
    project_works = relationship("ProjectWorks", back_populates="project_materials")

    project_material_creator = relationship(
        "Users", back_populates="created_project_materials"
    )

    def __repr__(self):
        return f"<ProjectMaterials(project_material_id={self.project_material_id})>"

    def to_dict(self):
        return {
            "project_material_id": str(self.project_material_id),
            "project": str(self.project),
            "material": str(self.material),
            "quantity": self.quantity,
            "project_work": str(self.project_work) if self.project_work else None,  # type: ignore
            "created_by": str(self.created_by),
            "created_at": self.created_at,
        }
