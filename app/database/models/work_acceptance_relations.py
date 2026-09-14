from uuid import uuid4

from sqlalchemy import UUID, Column, ForeignKey, Numeric
from sqlalchemy.orm import relationship

from app.database.db_setup import Base


class WorkAcceptanceRelations(Base):
    __tablename__ = "work_acceptance_relations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    acceptance_id = Column(
        UUID(as_uuid=True), ForeignKey("acceptances.id", ondelete="CASCADE"), nullable=False
    )
    work_id = Column(UUID(as_uuid=True), ForeignKey("works.work_id"), nullable=False)
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)

    acceptance = relationship("Acceptances", back_populates="work_acceptance_relations")
    work = relationship("Works", back_populates="work_acceptance_relations")

    def to_dict(self):
        return {
            "id": str(self.id),
            "acceptance_id": str(self.acceptance_id),
            "work_id": str(self.work_id),
            "quantity": self.quantity,
        }
