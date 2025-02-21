import uuid
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database.db_setup import Base


class Subscriptions(Base):
    __tablename__ = 'subscriptions'

    subscription_id = Column(UUID(as_uuid=True), primary_key=True,
                             default=uuid.uuid4, unique=True, nullable=False)
    user = Column(UUID, ForeignKey('users.user_id'), nullable=False)
    # JSON-строка данных о подписке
    # subscription_data = Column(Text, nullable=False)
    endpoint = Column(Text, nullable=False)
    keys = Column(Text, nullable=False)

    users = relationship("Users", back_populates="subscription")

    def __repr__(self):
        return f"<Subscription(id={self.subscription_id})>"

    def to_dict(self):
        return {
            "subscription_id": str(self.subscription_id),
            "user": str(self.user),
            "endpoint": self.endpoint,
            "keys": self.keys
            # "subscription_data": self.subscription_data
        }
