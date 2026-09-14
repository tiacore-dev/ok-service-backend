from uuid import uuid4

from sqlalchemy import UUID, BigInteger, Boolean, Column, ForeignKey, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_milliseconds


class ProjectWorks(Base):
    __tablename__ = "project_works"

    project_work_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    project_work_name = Column(String, nullable=True)
    work = Column(UUID, ForeignKey("works.work_id"), nullable=False)
    project = Column(
        UUID, ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False
    )
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)
    price = Column(Numeric(precision=10, scale=2), nullable=True)
    summ = Column(Numeric(precision=10, scale=2), nullable=True)
    signed = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        BigInteger,
        default=utc_epoch_milliseconds,
        server_default=text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
        nullable=False,
    )
    created_by = Column(UUID, ForeignKey("users.user_id"), nullable=False)

    works = relationship("Works", back_populates="project_work")
    projects = relationship("Projects", back_populates="project_work")

    project_work_creator = relationship("Users", back_populates="created_project_works")

    shift_report_details = relationship(
        "ShiftReportDetails", back_populates="project_works"
    )
    project_materials = relationship(
        "ProjectMaterials", back_populates="project_works"
    )

    def __repr__(self):
        return f"<ProjectWorks(project_work_id={self.project_work_id})>"

    def to_dict(self):
        return {
            "project_work_id": str(self.project_work_id),
            "project_work_name": self.project_work_name
            if self.project_work_name  # type: ignore
            else None,
            "work": str(self.work),
            "project": str(self.project),
            "quantity": self.quantity,
            "price": self.price if self.price is not None else None,
            "summ": self.summ if self.summ is not None else None,  # type: ignore
            "created_by": str(self.created_by),
            "created_at": self.created_at,
            "signed": self.signed,
        }
