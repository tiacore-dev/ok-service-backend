from uuid import uuid4
from datetime import datetime
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, UUID, ForeignKey, Boolean, CheckConstraint
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
        'users.user_id'), nullable=False)
    created_at = Column(Integer, default=lambda: int(datetime.utcnow().timestamp()),
                        server_default=text("EXTRACT(EPOCH FROM NOW())"), nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint("category IN (0, 1, 2, 3, 4)", name="check_category_values"),
    )

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

    shift_report = relationship(
        "ShiftReports", back_populates="users", foreign_keys="[ShiftReports.user]")
    created_shift_reports = relationship(
        "ShiftReports", back_populates="shift_report_creator", foreign_keys="[ShiftReports.created_by]")

    subscription = relationship("Subscriptions", back_populates="users")

    created_project_schedules = relationship(
        "ProjectSchedules", back_populates="project_schedule_creator")
    created_project_works = relationship(
        "ProjectWorks", back_populates="project_work_creator")
    created_shift_report_details = relationship(
        "ShiftReportDetails", back_populates="shift_report_details_creator")
    created_work_categories = relationship(
        "WorkCategories", back_populates="work_category_creator")
    created_work_prices = relationship(
        "WorkPrices", back_populates="work_price_creator")
    created_works = relationship("Works", back_populates="work_creator")

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
            "created_by": str(self.created_by),
            "created_at": self.created_at,
            "deleted": self.deleted
        }
