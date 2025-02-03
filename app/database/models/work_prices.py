from uuid import uuid4
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, UUID, ForeignKey, Boolean, Numeric
from app.database.db_setup import Base


class WorkPrices(Base):
    __tablename__ = 'work_prices'

    work_price_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    work = Column(UUID, ForeignKey('works.work_id'))
    category = Column(Integer, nullable=False)
    price = Column(Numeric(precision=10, scale=2), nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)

    works = relationship("Works", back_populates="work_price")

    def to_dict(self):
        # Проверяем, есть ли роль
        # work_data = self.works.to_dict() if self.works else str(self.work)
        return {
            "work_price_id": str(self.work_price_id),
            "work": self.work,
            "category": self.category if self.category else None,
            "price": self.price if self.price else None,
            "deleted": self.deleted
        }
