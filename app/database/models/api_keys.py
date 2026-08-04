from uuid import uuid4

from sqlalchemy import UUID, BigInteger, Column, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database.db_setup import Base
from app.database.time_utils import utc_epoch_milliseconds


class ApiKeys(Base):
    __tablename__ = "api_keys"

    api_key_id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    name = Column(String, nullable=False)
    token = Column(String, nullable=False)
    expires_at = Column(BigInteger, nullable=True)
    created_at = Column(
        BigInteger,
        default=utc_epoch_milliseconds,
        server_default=text("CAST(EXTRACT(EPOCH FROM NOW()) * 1000 AS BIGINT)"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("name", name="uq_api_keys_name"),
        UniqueConstraint("token", name="uq_api_keys_token"),
    )

    permissions = relationship(
        "KeyPermissionTypeRelations",
        back_populates="api_key",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<ApiKeys(api_key_id={self.api_key_id}, name={self.name})>"

    def to_dict(self):
        return {
            "api_key_id": str(self.api_key_id),
            "name": self.name,
            "token": self.token,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
        }

    def to_public_dict(self):
        return {
            "api_key_id": str(self.api_key_id),
            "name": self.name,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
        }
