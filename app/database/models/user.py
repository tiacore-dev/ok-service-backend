from uuid import uuid4
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
    deleted = Column(Boolean, nullable=False, default=False)

    roles = relationship("Roles", back_populates="user")
    project = relationship("Projects", back_populates="user")
    shift_report = relationship("ShiftReports", back_populates="users")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        # Проверяем, есть ли роль
        role_data = self.roles.to_dict() if self.roles else self.role
        return {
            "user_id": str(self.user_id),
            "login": self.login,
            "name": self.name,
            # "role": self.role,
            "role": role_data,
            "category": self.category if self.category else None,
            "deleted": self.deleted
        }
