from uuid import uuid4

from sqlalchemy import UUID, BigInteger, Boolean, Column, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_milliseconds


class Cities(Base):
    __tablename__ = "cities"

    city_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    name = Column(String, nullable=False, unique=True)
    created_at = Column(
        BigInteger,
        default=utc_epoch_milliseconds,
        server_default=text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
        nullable=False,
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey(
            "users.user_id",
            name="cities_created_by_fkey",
            use_alter=True,
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    deleted = Column(Boolean, nullable=False, default=False)

    creator = relationship(
        "Users",
        back_populates="created_cities",
        foreign_keys=[created_by],
        passive_deletes=True,
    )
    users = relationship("Users", back_populates="city", foreign_keys="Users.city_id")
    objects = relationship("Objects", back_populates="city")

    def __repr__(self):
        return f"<Cities(city_id={self.city_id}, name={self.name}, deleted={
            self.deleted
        })>"

    def to_dict(self):
        return {
            "city_id": str(self.city_id),
            "name": self.name,
            "created_at": self.created_at,
            "created_by": str(self.created_by),
            "deleted": self.deleted,
        }
