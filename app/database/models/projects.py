from uuid import uuid4
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, UUID, ForeignKey, Boolean
from app.database.db_setup import Base


class Projects(Base):
    __tablename__ = 'projects'

    project_id = Column(UUID(as_uuid=True), primary_key=True,
                        default=uuid4, nullable=False)
    name = Column(String, nullable=False)
    object = Column(UUID, ForeignKey('objects.object_id'), nullable=False)
    project_leader = Column(UUID, ForeignKey('users.user_id'), nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)

    objects = relationship("Objects", back_populates="project")
    user = relationship("Users", back_populates="project")
    shift_report = relationship("ShiftReports", back_populates="projects")
    project_work = relationship("ProjectWorks", back_populates="projects")

    def to_dict(self):
        # Проверяем, есть ли роль
        # object_data = self.objects.to_dict() if self.objects else str(self.object)
        # user_data = self.user.to_dict() if self.user else str(self.project_leader)
        return {
            "project_id": str(self.project_id),
            "name": self.name,
            "object": self.object,
            "project_leader": self.project_leader,
            "deleted": self.deleted
        }
