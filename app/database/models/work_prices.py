from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    Numeric,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base


class WorkPrices(Base):
    __tablename__ = "work_prices"

    work_price_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    work = Column(UUID, ForeignKey("works.work_id"))
    category = Column(Integer, nullable=False, default=0)
    price = Column(Numeric(precision=10, scale=2), nullable=False)
    created_at = Column(
        BigInteger,
        default=lambda: int(datetime.utcnow().timestamp()),
        server_default=text("EXTRACT(EPOCH FROM NOW())"),
        nullable=False,
    )
    created_by = Column(UUID, ForeignKey("users.user_id"), nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint(
            "category IN (0, 1, 2, 3, 4)", name="check_products_category_values"
        ),
    )

    works = relationship("Works", back_populates="work_price")

    work_price_creator = relationship("Users", back_populates="created_work_prices")

    def __repr__(self):
        return (
            f"<WorkPrices(work_price_id={self.work_price_id}, work={self.work}, "
            f"category={self.category}, price={self.price}, deleted={self.deleted})>"
        )

    def to_dict(self):
        return {
            "work_price_id": str(self.work_price_id),
            "work": str(self.work),
            "category": self.category if self.category else None,  # type: ignore
            "price": self.price if self.price else None,  # type: ignore
            "created_by": str(self.created_by),
            "created_at": self.created_at,
            "deleted": self.deleted,
        }
