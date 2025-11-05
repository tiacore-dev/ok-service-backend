from datetime import datetime
from enum import Enum as PyEnum
from uuid import uuid4

from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    Column,
    Enum,
    ForeignKey,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base


class AbsenceReason(PyEnum):
    VACATION = "vacation"
    SICK_LEAVE = "sick_leave"
    DAY_OFF = "day_off"


class Leaves(Base):
    __tablename__ = "leaves"

    leave_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    start_date = Column(BigInteger, nullable=False)
    end_date = Column(BigInteger, nullable=False)
    reason = Column(
        Enum(
            AbsenceReason,
            name="absence_reason_enum",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    responsible_id = Column(
        UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False
    )
    comment = Column(String, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    created_at = Column(
        BigInteger,
        default=lambda: int(datetime.utcnow().timestamp()),
        server_default=text("EXTRACT(EPOCH FROM NOW())"),
        nullable=False,
    )
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    updated_at = Column(BigInteger, nullable=True)
    deleted = Column(Boolean, nullable=False, default=False)

    user = relationship("Users", back_populates="leaves", foreign_keys=[user_id])
    responsible = relationship(
        "Users", back_populates="responsible_leaves", foreign_keys=[responsible_id]
    )
    created_by_user = relationship(
        "Users", back_populates="created_leaves", foreign_keys=[created_by]
    )
    updated_by_user = relationship(
        "Users", back_populates="updated_leaves", foreign_keys=[updated_by]
    )

    def __repr__(self):
        return (
            f"<Leaves(leave_id={self.leave_id}, user_id={self.user_id}, "
            f"start_date={self.start_date}, end_date={self.end_date}, reason={self.reason})>"
        )

    def to_dict(self):
        return {
            "leave_id": str(self.leave_id),
            "start_date": self.start_date,
            "end_date": self.end_date,
            "reason": self.reason.value,
            "user": str(self.user_id),
            "responsible": str(self.responsible_id),
            "comment": self.comment,
            "created_by": str(self.created_by),
            "created_at": self.created_at,
            "updated_by": str(self.updated_by) if self.updated_by else None,  # type: ignore
            "updated_at": self.updated_at,
            "deleted": self.deleted,
        }
