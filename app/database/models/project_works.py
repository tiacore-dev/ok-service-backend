from uuid import uuid4
from sqlalchemy.orm import relationship
from sqlalchemy import Column, UUID, ForeignKey, Boolean, Numeric
from app.database.db_setup import Base


class ProjectWorks(Base):
    __tablename__ = 'project_works'

    project_work_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    work = Column(UUID, ForeignKey('works.work_id'), nullable=False)
    project = Column(UUID, ForeignKey('projects.project_id'), nullable=False)
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)
    summ = Column(Numeric(precision=10, scale=2), nullable=True)
    signed = Column(Boolean, nullable=False, default=False)

    works = relationship("Works", back_populates="project_work")
    projects = relationship("Projects", back_populates="project_work")

    def __repr__(self):
        return (f"<ProjectWorks(project_work_id={self.project_work_id}, work={self.work}, "
                f"project={self.project}, quantity={self.quantity}, summ={self.summ}, signed={self.signed})>")

    def to_dict(self):

        return {
            "project_work_id": str(self.project_work_id),
            "work": self.work,
            "project": self.project,
            "quantity": self.quantity,
            "summ": self.summ if self.summ else None,
            "signed": self.signed
        }
