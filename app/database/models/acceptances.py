from enum import Enum
from uuid import uuid4

from sqlalchemy import UUID, BigInteger, CheckConstraint, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database.db_setup import Base


class AcceptanceStatusDB(str, Enum):
    PRESENTED = "presented"
    VIOLATIONS_FOUND = "violations_found"
    ACCEPTED_ON_SITE = "accepted_on_site"
    DOCUMENTS_SIGNED = "documents_signed"


class Acceptances(Base):
    __tablename__ = "acceptances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    date = Column(BigInteger, nullable=False)
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.project_id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String, nullable=False, default=AcceptanceStatusDB.PRESENTED.value)
    comment = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('presented', 'violations_found', 'accepted_on_site', 'documents_signed')",
            name="check_acceptances_status",
        ),
    )

    project = relationship("Projects", back_populates="acceptances")
    work_acceptance_relations = relationship(
        "WorkAcceptanceRelations",
        back_populates="acceptance",
        cascade="all, delete-orphan",
    )
    status_history = relationship(
        "AcceptanceStatusHistory", back_populates="acceptance"
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "date": self.date,
            "project_id": str(self.project_id),
            "status": self.status,
            "comment": self.comment,
        }
