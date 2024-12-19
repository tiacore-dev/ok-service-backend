from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.database.db_setup import Base


class Roles(Base):
    __tablename__ = 'roles'

    role_id = Column(String, primary_key=True, nullable=False)
    name = Column(String, nullable=False)

    user = relationship("Users", back_populates="roles")

    def to_dict(self):
        return {
            "role_id": self.role_id,
            "name": self.name
        }
