from uuid import uuid4

from sqlalchemy import UUID, Boolean, Column, Date, ForeignKey, Numeric, Text
from sqlalchemy.orm import relationship

from app.database.db_setup import Base


class WorkPlans(Base):
    __tablename__ = "work_plans"

    work_plan_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    user_id = Column(UUID, ForeignKey("users.user_id"), nullable=True)
    date = Column(Date, nullable=False)
    summ = Column(Numeric(precision=12, scale=2), nullable=False)
    description = Column(Text, nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)

    users = relationship("Users", back_populates="work_plans")

    def to_dict(self):
        return {
            "work_plan_id": str(self.work_plan_id),
            "user_id": str(self.user_id) if self.user_id is not None else None,
            "date": self.date,
            "summ": self.summ,
            "description": self.description,
            "deleted": self.deleted,
        }
