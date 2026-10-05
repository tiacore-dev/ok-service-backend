from uuid import uuid4

from sqlalchemy import UUID, BigInteger, Column, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_milliseconds


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
    price = Column(Numeric(precision=10, scale=2), nullable=True)
    summ = Column(Numeric(precision=20, scale=4), nullable=True)
    project_work = Column(
        UUID, ForeignKey("project_works.project_work_id"), nullable=True
    )
    created_at = Column(
        BigInteger,
        default=utc_epoch_milliseconds,
        server_default=text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
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
            "price": self.price if self.price is not None else None,
            "summ": self.summ if self.summ is not None else None,  # type: ignore
            "project_work": str(self.project_work) if self.project_work else None,  # type: ignore
            "created_by": str(self.created_by),
            "created_at": self.created_at,
        }
