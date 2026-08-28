from uuid import uuid4

from sqlalchemy import UUID, BigInteger, CheckConstraint, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database.db_setup import Base


class AcceptanceStatusHistory(Base):
    __tablename__ = "acceptance_status_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    acceptance_id = Column(UUID(as_uuid=True), ForeignKey("acceptances.id"), nullable=False)
    changed_at = Column(BigInteger, nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    from_status = Column(String, nullable=False)
    to_status = Column(String, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "from_status IN ('presented', 'violations_found', 'accepted_on_site', 'documents_signed')",
            name="check_acceptance_history_from_status",
        ),
        CheckConstraint(
            "to_status IN ('presented', 'violations_found', 'accepted_on_site', 'documents_signed')",
            name="check_acceptance_history_to_status",
        ),
    )

    acceptance = relationship("Acceptances", back_populates="status_history")
    changed_by_user = relationship("Users", back_populates="acceptance_status_history")

    def to_dict(self):
        return {
            "id": str(self.id),
            "acceptance_id": str(self.acceptance_id),
            "changed_at": self.changed_at,
            "changed_by": str(self.changed_by),
            "from_status": self.from_status,
            "to_status": self.to_status,
        }
