from uuid import uuid4
from datetime import datetime
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, UUID, ForeignKey, Boolean
from werkzeug.security import generate_password_hash, check_password_hash
from app.database.db_setup import Base


class Users(Base):
    __tablename__ = 'users'

    user_id = Column(UUID(as_uuid=True), primary_key=True,
                     default=uuid4, nullable=False)
    login = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, ForeignKey('roles.role_id'), nullable=False)
    category = Column(Integer, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey(
        'users.user_id'), nullable=True)
    created_at = Column(Integer, default=lambda: int(datetime.utcnow().timestamp()),
                        server_default=text("EXTRACT(EPOCH FROM NOW())"))
    deleted = Column(Boolean, nullable=False, default=False)

    roles = relationship("Roles", back_populates="user")

    # Явно указываем foreign_keys для связи с `Projects`
    led_projects = relationship(
        "Projects", back_populates="leader", foreign_keys="[Projects.project_leader]")
    created_projects = relationship(
        "Projects", back_populates="project_creator", foreign_keys="[Projects.created_by]")

    # Objects
    managed_objects = relationship(
        "Objects", back_populates="object_manager", foreign_keys="[Objects.manager]")
    created_objects = relationship(
        "Objects",  back_populates="object_creator", foreign_keys="[Objects.created_by]")

    shift_report = relationship("ShiftReports", back_populates="users")
    subscription = relationship("Subscriptions", back_populates="users")

    # Самореференсная связь
    creator = relationship("Users", remote_side=[
                           user_id], backref="created_users")

    def __repr__(self):
        return (f"<Users(user_id={self.user_id}, login={self.login}, name={self.name}, "
                f"role={self.role}, category={self.category}, deleted={self.deleted})>")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "user_id": str(self.user_id),
            "login": self.login,
            "name": self.name,
            "role": self.role,
            "category": self.category if self.category else None,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "deleted": self.deleted
        }
