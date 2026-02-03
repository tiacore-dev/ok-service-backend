from datetime import datetime
from uuid import uuid4

from sqlalchemy import UUID, BigInteger, Column, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base


class WorkMaterialRelations(Base):
    __tablename__ = "work_material_relations"

    work_material_relation_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    work = Column(UUID, ForeignKey("works.work_id"), nullable=False)
    material = Column(
        UUID, ForeignKey("materials.material_id", ondelete="CASCADE"), nullable=False
    )
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)

    created_at = Column(
        BigInteger,
        default=lambda: int(datetime.utcnow().timestamp()),
        server_default=text("EXTRACT(EPOCH FROM NOW())"),
        nullable=False,
    )
    created_by = Column(UUID, ForeignKey("users.user_id"), nullable=False)

    works = relationship("Works", back_populates="material_works")
    materials = relationship("Materials", back_populates="work_materials")

    work_material_relation_creator = relationship(
        "Users", back_populates="created_work_material_relations"
    )

    def __repr__(self):
        return f"<ProjectWorks(work_material_relation_id={
            self.work_material_relation_id
        })>"

    def to_dict(self):
        return {
            "work_material_relation_id": str(self.work_material_relation_id),
            "work": str(self.work),
            "material": str(self.material),
            "quantity": self.quantity,
            "created_by": str(self.created_by),
            "created_at": self.created_at,
        }
