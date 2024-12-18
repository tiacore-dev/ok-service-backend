from sqlalchemy import Column, Integer, String, UUID, ForeignKey, Boolean, Numeric
from app.database.db_setup import Base 
from uuid import uuid4
from sqlalchemy.orm import relationship


class WorkPrices(Base):
    __tablename__ = 'work_prices'
    
    work_price_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    work_id = Column(UUID, ForeignKey('works.work_id'))
    name = Column(String, nullable=False)
    category = Column(Integer, nullable=False)
    price = Column(Numeric(precision=10, scale=2), nullable=False)
    deleted = Column(Boolean, nullable=False, default=False)
    
    work = relationship("Works", back_populates="work_price")


    def to_dict(self):
        # Проверяем, есть ли роль
        #role_data = self.role_obj.to_dict() if self.role_obj else None
        return {
            "work_price_id": str(self.work_price_id),
            "work_id": self.work_id,
            "name": self.name,
            "category": self.category if self.category else None,
            "price": self.price if self.price else None,
            "deleted": self.deleted
        }
