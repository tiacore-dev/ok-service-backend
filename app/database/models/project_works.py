from uuid import uuid4
from datetime import datetime
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from sqlalchemy import Column, UUID, ForeignKey, Boolean, Numeric, BigInteger, String
from app.database.db_setup import Base


class ProjectWorks(Base):
    __tablename__ = 'project_works'

    project_work_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    project_work_name = Column(String, nullable=True)
    work = Column(UUID, ForeignKey('works.work_id'), nullable=False)
    project = Column(
        UUID,
        ForeignKey('projects.project_id', ondelete='CASCADE'),
        nullable=False
    )
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)
    summ = Column(Numeric(precision=10, scale=2), nullable=True)
    signed = Column(Boolean, nullable=False, default=False)
    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()),
                        server_default=text("EXTRACT(EPOCH FROM NOW())"), nullable=False)
    created_by = Column(UUID, ForeignKey(
        'users.user_id'), nullable=False)

    works = relationship("Works", back_populates="project_work")
    projects = relationship("Projects", back_populates="project_work")

    project_work_creator = relationship(
        "Users", back_populates="created_project_works")

    shift_report_details = relationship(
        "ShiftReportDetails", back_populates="project_works")

    def __repr__(self):
        return f"<ProjectWorks(project_work_id={self.project_work_id})>"

    def to_dict(self):

        return {
            "project_work_id": str(self.project_work_id),
            "project_work_name": self.project_work_name if self.project_work_name else None,
            "work": str(self.work),
            "project": str(self.project),
            "quantity": self.quantity,
            "summ": self.summ if self.summ else None,
            "created_by": str(self.created_by),
            "created_at": self.created_at,
            "signed": self.signed
        }
