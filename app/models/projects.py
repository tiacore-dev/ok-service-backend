from sqlalchemy import Column, String, UUID, ForeignKey, Boolean
from app.database.db_setup import Base 
from uuid import uuid4
from sqlalchemy.orm import relationship


class Projects(Base):
    __tablename__ = 'projects'
    
    project_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    name = Column(String, nullable=False)
    object_id = Column(String, ForeignKey('objects.object_id'), nullable=False)
    project_leader = Column(UUID, ForeignKey('users.user_id'),nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)
    
    object = relationship("Objects", back_populates="project")
    user = relationship("Users", back_populates="project")
    shift_report = relationship("ShiftReports", back_populates="project")


    def to_dict(self):
        # Проверяем, есть ли роль
        #role_data = self.role_obj.to_dict() if self.role_obj else None
        return {
            "project_id": self.project_id,
            "name": self.name,
            "object_id": self.object_id,
            "project_leader": self.project_leader if self.project_leader else None,
            "deleted": self.deleted
        }
