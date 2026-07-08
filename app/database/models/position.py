from uuid import uuid4

from sqlalchemy import UUID, BigInteger, Column, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_seconds


class Positions(Base):
    __tablename__ = "positions"

    position_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    name = Column(String, nullable=False)

    created_at = Column(
        BigInteger,
        default=utc_epoch_seconds,
        server_default=text("EXTRACT(EPOCH FROM NOW())"),
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable=True,
    )

    position_creator = relationship(
        "Users", back_populates="created_positions", foreign_keys=[created_by]
    )
    users = relationship(
        "Users", back_populates="position", foreign_keys="[Users.position_id]"
    )

    def __repr__(self):
        return f"<Positions(position_id={self.position_id}, name={self.name} "

    def to_dict(self):
        return {
            "position_id": str(self.position_id),
            "name": self.name,
            "created_at": self.created_at,
            "created_by": str(self.created_by)
            if self.created_by is not None
            else None,
        }
