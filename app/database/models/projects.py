from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from sqlalchemy import Column, String, UUID, ForeignKey, Boolean, BigInteger
from app.database.db_setup import Base


class Projects(Base):
    __tablename__ = 'projects'

    project_id = Column(UUID(as_uuid=True), primary_key=True,
                        default=uuid4, nullable=False)
    name = Column(String, nullable=False)
    object = Column(UUID, ForeignKey('objects.object_id'), nullable=False)
    project_leader = Column(UUID, ForeignKey('users.user_id'), nullable=True)
    night_shift_available = Column(Boolean, nullable=False, default=False)
    extreme_conditions_available = Column(
        Boolean, nullable=False, default=False)
    created_at = Column(BigInteger, default=lambda: int(datetime.utcnow().timestamp()),
                        server_default=text("EXTRACT(EPOCH FROM NOW())"))
    created_by = Column(UUID(as_uuid=True), ForeignKey(
        'users.user_id'), nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)

    objects = relationship("Objects", back_populates="project")

    # Указываем foreign_keys, чтобы явно указать, по какому полю связываются таблицы
    leader = relationship(
        "Users", back_populates="led_projects", foreign_keys=[project_leader])
    project_creator = relationship(
        "Users", back_populates="created_projects", foreign_keys=[created_by])

    shift_report = relationship("ShiftReports", back_populates="projects")
    project_work = relationship(
        "ProjectWorks",
        back_populates="projects",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    project_schedule = relationship(
        "ProjectSchedules", back_populates="projects")

    def __repr__(self):
        return (f"<Projects(project_id={self.project_id}, name={self.name}, "
                f" deleted={self.deleted})>")

    def to_dict(self):
        return {
            "project_id": str(self.project_id),
            "name": self.name,
            "object": str(self.object),
            "project_leader": str(self.project_leader),
            "night_shift_available": self.night_shift_available,
            "extreme_conditions_available": self.extreme_conditions_available,
            "created_at": self.created_at,
            "created_by": str(self.created_by),
            "deleted": self.deleted
        }
